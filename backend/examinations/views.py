from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.permissions import IsAdmin, require_permission, require_any_permission
from accounts.rbac import user_has_permission
from accounts.audit import log_audit
from students.models import Student
from academics.models import CourseOffering
from enrollments.models import CourseRegistration
from .models import (
    ExamType, Examination, Grade, Marks, FinalGrade, Result, ResultApproval,
    MarksEditPermission, OfferingMarksEditRequest,
)
from .marks_locking import can_edit_exam_marks, exam_edit_status, get_semester_phase, get_mid_term_cutoff, get_grace_end, offering_submission_locked
from .duration_utils import parse_unlock_duration, format_unlock_duration
from .serializers import (
    ExamTypeSerializer, ExaminationSerializer,
    GradeSerializer, MarksSerializer, FinalGradeSerializer,
    ResultSerializer, ResultApprovalSerializer, MarksEditPermissionSerializer,
    OfferingMarksEditRequestSerializer,
)


CATEGORY_WEIGHT_CAP = {
    'quiz': Decimal('10'),
    'assignment': Decimal('10'),
    'presentation': Decimal('10'),
}


def _category_weight_used(offering, category: str) -> Decimal:
    total = Decimal('0')
    for exam in Examination.objects.filter(offering=offering, assessment_category=category):
        if exam.weight_percentage is not None:
            total += Decimal(str(exam.weight_percentage))
    return total


# ── EXAM TYPES ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_exam_types(request):
    return Response(ExamTypeSerializer(ExamType.objects.all(), many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_exam_type(request):
    serializer = ExamTypeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── GRADE SCALE ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_grades(request):
    return Response(GradeSerializer(Grade.objects.all().order_by('-min_percentage'), many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_grade(request):
    serializer = GradeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── EXAMINATIONS ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'examinations.view_examination', 'examinations.create_examination',
    'examinations.enter_marks', 'examinations.view_marks',
)])
def list_examinations(request):
    exams = Examination.objects.select_related('course', 'semester', 'offering', 'exam_type').all()
    offering = request.query_params.get('offering', request.query_params.get('section'))

    if request.user.user_type == 'teacher':
        faculty = _get_faculty(request.user)
        if not faculty:
            return Response([])
        exams = exams.filter(offering__faculty=faculty)
        if not offering:
            return Response([])
        try:
            owned_offering = CourseOffering.objects.get(offering_id=offering, faculty=faculty)
        except CourseOffering.DoesNotExist:
            return Response({'error': 'Course not found or not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
        if not owned_offering.is_active or offering_submission_locked(owned_offering):
            return Response(
                {'error': 'Marks can only be entered for active, incomplete courses.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        from .assessment_setup import ensure_offering_assessments
        ensure_offering_assessments(owned_offering, created_by=request.user)

    semester = request.query_params.get('semester')
    if semester:
        exams = exams.filter(semester__semester_id=semester)
    if offering:
        exams = exams.filter(offering__offering_id=offering)
    if request.user.user_type == 'teacher':
        exams = exams.filter(
            Q(assessment_category__in=['mid_term', 'final'])
            | Q(
                assessment_category__in=['quiz', 'assignment', 'presentation'],
                weight_percentage__isnull=False,
                weight_percentage__gt=0,
            )
        )
    exams = exams.order_by('assessment_category', 'exam_name')
    return Response(ExaminationSerializer(exams, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.create_examination')])
def create_examination(request):
    if request.user.user_type == 'teacher':
        faculty = _get_faculty(request.user)
        offering_id = request.data.get('offering', request.data.get('section'))
        if not faculty:
            return Response({'error': 'Faculty profile required.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            offering = CourseOffering.objects.get(offering_id=offering_id)
        except CourseOffering.DoesNotExist:
            return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)
        if offering.faculty_id != faculty.faculty_id:
            return Response({'error': 'You can only create exams for your own courses.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = ExaminationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def semester_assessment_status(request):
    """Assessment setup overview for a semester."""
    from .assessment_setup import get_semester_assessment_status

    semester_id = request.query_params.get('semester_id')
    if not semester_id:
        from academics.models import Semester
        current = Semester.objects.filter(is_current=True).first()
        if not current:
            return Response({'error': 'No semester specified and no current semester set.'}, status=status.HTTP_400_BAD_REQUEST)
        semester_id = current.semester_id

    result = get_semester_assessment_status(semester_id)
    if result.get('error'):
        return Response(result, status=status.HTTP_404_NOT_FOUND)
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def initialize_semester_assessments(request):
    """Bulk-create standard assessments for all offerings in a semester."""
    from .assessment_setup import initialize_semester_assessments as do_initialize

    semester_id = request.data.get('semester_id')
    if not semester_id:
        return Response({'error': 'semester_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    result = do_initialize(semester_id, created_by=request.user)
    if result.get('error'):
        return Response(result, status=status.HTTP_404_NOT_FOUND)

    log_audit(request, 'initialize_semester_assessments', 'semester', semester_id, new_value=result)
    return Response({
        'message': (
            f'Created {result["exams_created"]} assessment(s) across '
            f'{result["offerings_processed"]} course assignment(s).'
        ),
        **result,
    })


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, require_any_permission(
    'examinations.view_examination', 'examinations.update_examination',
    'examinations.delete_examination',
)])
def examination_detail(request, exam_id):
    try:
        exam = Examination.objects.select_related('course', 'exam_type', 'offering__faculty').get(exam_id=exam_id)
    except Examination.DoesNotExist:
        return Response({'error': 'Examination not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(ExaminationSerializer(exam).data)

    if request.user.user_type == 'teacher':
        faculty = _get_faculty(request.user)
        if not faculty or exam.offering.faculty_id != faculty.faculty_id:
            return Response({'error': 'Not your section.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        if not user_has_permission(request.user, 'examinations.update_examination'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        if request.user.user_type != 'admin' and offering_submission_locked(exam.offering):
            return Response(
                {'error': 'Course marks are locked. Request admin approval to edit assessments.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if exam.assessment_category in ('mid_term', 'final'):
            return Response({'error': 'Mid Term and Final weights are fixed (30% / 40%) and cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)
        if 'weight_percentage' in request.data and exam.assessment_category in CATEGORY_WEIGHT_CAP:
            weight_dec = Decimal(str(request.data['weight_percentage']))
            cap = CATEGORY_WEIGHT_CAP[exam.assessment_category]
            if weight_dec <= 0 or weight_dec > cap:
                return Response(
                    {'error': f'weight_percentage must be between 0 and {cap} for {exam.assessment_category}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            used = _category_weight_used(exam.offering, exam.assessment_category)
            if exam.weight_percentage is not None:
                used -= Decimal(str(exam.weight_percentage))
            if used + weight_dec > cap:
                return Response(
                    {'error': f'{exam.assessment_category.title()} assessments cannot exceed {cap}% (currently {used}%, requested {weight_dec}%).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            continuous_total = sum(_category_weight_used(exam.offering, c) for c in CATEGORY_WEIGHT_CAP)
            if exam.weight_percentage is not None:
                continuous_total -= Decimal(str(exam.weight_percentage))
            if continuous_total + weight_dec > Decimal('30'):
                return Response(
                    {'error': f'Total continuous weight cannot exceed 30% (would be {continuous_total + weight_dec}%).'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer = ExaminationSerializer(exam, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if not user_has_permission(request.user, 'examinations.delete_examination'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    if request.user.user_type != 'admin' and offering_submission_locked(exam.offering):
        return Response(
            {'error': 'Course marks are locked. Request admin approval to delete assessments.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    exam.delete()
    return Response({'message': 'Examination deleted.'}, status=status.HTTP_204_NO_CONTENT)


# ── MARKS ─────────────────────────────────────────────────────

def _get_faculty(user):
    try:
        return user.faculty_profile
    except Exception:
        return None


def _can_edit_offering_marks(offering, user, student_id=None):
    """Legacy offering-level check; prefer can_edit_exam_marks for exam-aware locking."""
    if user.user_type == 'admin':
        return True
    if offering_submission_locked(offering):
        faculty = _get_faculty(user)
        if not faculty:
            return False
        perms = MarksEditPermission.objects.filter(
            offering=offering, granted_to=faculty, is_active=True,
            request_status='approved', expires_at__gt=timezone.now(),
        )
        if student_id:
            return perms.filter(student_id=student_id).exists()
        return perms.exists()
    return True


def _get_exam_for_marks(exam_id):
    return Examination.objects.select_related(
        'offering', 'offering__faculty', 'exam_type', 'semester',
    ).get(exam_id=exam_id)


def _grade_for_percentage(pct):
    from examinations.results_pipeline import grade_for_percentage
    return grade_for_percentage(pct)


def _compute_offering_final_grades(offering):
    from examinations.results_pipeline import compute_offering_final_grades
    return compute_offering_final_grades(offering)


def _exam_weight_percentage(exam) -> Decimal:
    if exam.weight_percentage is not None:
        return Decimal(str(exam.weight_percentage))
    return exam.exam_type.weightage_percentage


def _sync_student_cgpa(student):
    from examinations.results_pipeline import (
        compute_student_cgpa,
        compute_student_earned_credit_hours,
        refresh_student_academic_record,
    )
    refresh_student_academic_record(student)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'examinations.view_examination', 'examinations.create_examination',
    'examinations.enter_marks', 'examinations.view_marks',
)])
def marks_lock_status(request):
    """Per-exam or per-section marks lock overview for teachers."""
    offering_id = request.query_params.get('offering_id')
    exam_id = request.query_params.get('exam_id')

    if exam_id:
        try:
            exam = _get_exam_for_marks(exam_id)
        except Examination.DoesNotExist:
            return Response({'error': 'Examination not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.user_type == 'teacher':
            faculty = _get_faculty(request.user)
            if not faculty or exam.offering.faculty_id != faculty.faculty_id:
                return Response({'error': 'Not your section.'}, status=status.HTTP_403_FORBIDDEN)
        student_id = request.query_params.get('student_id')
        parsed_student_id = None
        if student_id:
            try:
                parsed_student_id = int(student_id)
            except (TypeError, ValueError):
                return Response({'error': 'Invalid student_id.'}, status=status.HTTP_400_BAD_REQUEST)
        base = exam_edit_status(exam, request.user, student_id=parsed_student_id)
        if student_id:
            return Response(base)
        from enrollments.repeat_utils import roster_eligible_registrations
        students = []
        for reg in roster_eligible_registrations(exam.offering).select_related('student'):
            st = exam_edit_status(exam, request.user, student_id=reg.student_id)
            students.append({
                'student_id': reg.student_id,
                'registration_number': reg.student.registration_number,
                'editable': st['editable'],
                'admin_override': st.get('admin_override', False),
            })
        base['students'] = students
        return Response(base)

    if not offering_id:
        return Response({'error': 'offering_id or exam_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        offering = CourseOffering.objects.select_related('semester').get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.user_type == 'teacher':
        faculty = _get_faculty(request.user)
        if not faculty or offering.faculty_id != faculty.faculty_id:
            return Response({'error': 'Not your course.'}, status=status.HTTP_403_FORBIDDEN)

    semester = offering.semester
    exams = Examination.objects.select_related('exam_type').filter(offering=offering)
    return Response({
        'offering_id': offering.offering_id,
        'semester_phase': get_semester_phase(semester),
        'mid_term_cutoff': str(get_mid_term_cutoff(semester)),
        'grace_end': str(get_grace_end(semester)),
        'exams': [exam_edit_status(ex, request.user) for ex in exams],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission(
    'examinations.view_examination', 'examinations.create_examination',
    'examinations.enter_marks', 'examinations.view_marks',
)])
def list_marks(request, exam_id):
    try:
        exam = _get_exam_for_marks(exam_id)
    except Examination.DoesNotExist:
        return Response({'error': 'Examination not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.user_type == 'teacher':
        faculty = _get_faculty(request.user)
        if not faculty or exam.offering.faculty_id != faculty.faculty_id:
            return Response({'error': 'Not your section.'}, status=status.HTTP_403_FORBIDDEN)

    marks = Marks.objects.select_related('student', 'exam').filter(exam__exam_id=exam_id)
    return Response(MarksSerializer(marks, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.enter_marks')])
def enter_marks(request, exam_id):
    try:
        exam = _get_exam_for_marks(exam_id)
    except Examination.DoesNotExist:
        return Response({'error': 'Examination not found.'}, status=status.HTTP_404_NOT_FOUND)

    faculty = _get_faculty(request.user)
    if request.user.user_type == 'teacher' and not faculty:
        return Response({'error': 'Only faculty can enter marks.'}, status=status.HTTP_403_FORBIDDEN)
    if not faculty:
        faculty = exam.offering.faculty

    marks_data = request.data.get('marks', [])
    created = []
    errors  = []

    for entry in marks_data:
        student_id = entry.get('student')
        if not student_id:
            errors.append({'error': 'Each marks entry must include a student id.'})
            continue
        allowed, reason = can_edit_exam_marks(exam, request.user, student_id)
        if not allowed:
            errors.append({'student': student_id, 'error': reason})
            continue

        registration = CourseRegistration.objects.filter(
            offering=exam.offering,
            student_id=student_id,
            status='registered',
        ).first()
        if not registration:
            errors.append({'student': student_id, 'error': 'Student is not registered for this course offering.'})
            continue

        payload = {
            'obtained_marks': entry.get('obtained_marks'),
            'is_absent': entry.get('is_absent', False),
            'remarks': entry.get('remarks', ''),
        }
        existing = Marks.objects.filter(exam=exam, student_id=student_id).first()
        if existing:
            serializer = MarksSerializer(existing, data=payload, partial=True)
            if serializer.is_valid():
                serializer.save(modified_by=request.user)
                created.append(serializer.data)
            else:
                errors.append({'student': student_id, 'errors': serializer.errors})
            continue

        payload.update({
            'exam': exam_id,
            'student': student_id,
            'registration': registration.registration_id,
            'entered_by': faculty.faculty_id if faculty else entry.get('entered_by'),
        })
        serializer = MarksSerializer(data=payload)
        if serializer.is_valid():
            serializer.save()
            created.append(serializer.data)
        else:
            errors.append({'student': student_id, 'errors': serializer.errors})

    if not created and errors:
        status_code = status.HTTP_403_FORBIDDEN if any(
            e.get('error') and 'permission' in str(e.get('error', '')).lower()
            or 'locked' in str(e.get('error', '')).lower()
            for e in errors
        ) else status.HTTP_400_BAD_REQUEST
        return Response({'created': created, 'errors': errors}, status=status_code)
    return Response({'created': created, 'errors': errors}, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated, require_permission('examinations.enter_marks')])
def update_marks(request, marks_id):
    try:
        marks = Marks.objects.select_related('exam__offering', 'exam__exam_type', 'exam__semester').get(marks_id=marks_id)
    except Marks.DoesNotExist:
        return Response({'error': 'Marks record not found.'}, status=status.HTTP_404_NOT_FOUND)

    allowed, reason = can_edit_exam_marks(marks.exam, request.user, marks.student_id)
    if not allowed:
        return Response({'error': reason}, status=status.HTTP_403_FORBIDDEN)

    serializer = MarksSerializer(marks, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save(modified_by=request.user)
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── FINAL GRADES ──────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_final_grades(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)
    from django.db.models import Q
    from examinations.results_pipeline import published_semester_ids_for
    from enrollments.models import CourseRegistration

    published = published_semester_ids_for(student)
    locked_registration_ids = CourseRegistration.objects.filter(
        student=student,
        offering__marks_locked=True,
    ).values_list('registration_id', flat=True)
    grades = FinalGrade.objects.select_related('course', 'semester', 'grade').filter(
        student=student,
    ).filter(
        Q(semester_id__in=published) | Q(registration_id__in=locked_registration_ids),
    ).distinct()
    return Response(FinalGradeSerializer(grades, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_assessment_marks(request):
    """Assessment-level marks for the student's registered courses."""
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    from django.db.models import Q
    from .serializers import StudentMarksSerializer

    offering_ids = CourseRegistration.objects.filter(
        student=student,
    ).filter(
        Q(status='registered') | Q(offering__marks_locked=True),
    ).values_list('offering_id', flat=True).distinct()
    marks = Marks.objects.filter(
        student=student,
        exam__offering_id__in=offering_ids,
    ).select_related('exam', 'exam__course', 'exam__exam_type').order_by(
        'exam__course__course_code', 'exam__exam_name',
    )
    return Response(StudentMarksSerializer(marks, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_final_grade(request):
    serializer = FinalGradeSerializer(data=request.data)
    if serializer.is_valid():
        fg = serializer.save()
        from examinations.results_pipeline import sync_registration_from_final_grade
        sync_registration_from_final_grade(fg)
        log_audit(request, 'create_final_grade', 'final_grade', fg.final_grade_id)
        return Response(FinalGradeSerializer(fg).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── RESULTS ───────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_results(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)
    results = Result.objects.select_related('semester').filter(student=student, is_published=True)
    return Response(ResultSerializer(results, many=True).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_results(request):
    results = Result.objects.select_related('student', 'semester').all()
    semester = request.query_params.get('semester')
    if semester:
        results = results.filter(semester__semester_id=semester)
    return Response(ResultSerializer(results, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def generate_semester_results(request):
    """Aggregate FinalGrades into Result rows for a semester."""
    semester_id = request.data.get('semester_id')
    if not semester_id:
        return Response({'error': 'semester_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
    from academics.models import Semester
    try:
        semester = Semester.objects.get(semester_id=semester_id)
    except Semester.DoesNotExist:
        return Response({'error': 'Semester not found.'}, status=status.HTTP_404_NOT_FOUND)

    from examinations.results_pipeline import generate_results_for_semester
    stats = generate_results_for_semester(semester)
    log_audit(request, 'generate_results', 'semester', semester.semester_id, new_value=stats)
    return Response({'message': 'Results generated.', **stats})


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_result(request):
    serializer = ResultSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.publish_results')])
def publish_result(request, result_id):
    try:
        result = Result.objects.select_related('student', 'semester').get(result_id=result_id)
    except Result.DoesNotExist:
        return Response({'error': 'Result not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not ResultApproval.objects.filter(result=result).exists():
        return Response({'error': 'Result must be approved before publishing.'}, status=status.HTTP_400_BAD_REQUEST)

    if result.is_published:
        return Response({'error': 'Result is already published.'}, status=status.HTTP_400_BAD_REQUEST)

    result.is_published = True
    result.published_date = timezone.now().date()
    result.published_by = request.user
    result.save(update_fields=['is_published', 'published_date', 'published_by'])
    _sync_student_cgpa(result.student)

    from academics.policy_utils import apply_standing_after_publish
    from enrollments.promotion import promote_student_after_published_result
    standing = apply_standing_after_publish(
        result.student, result, performed_by=request.user,
    )
    promo = promote_student_after_published_result(
        result.student, result.semester, performed_by=request.user,
    )
    log_audit(request, 'publish_result', 'result', result.result_id, new_value={'student_id': result.student_id})
    return Response({
        'message': 'Result published.',
        'promotion': promo,
        'standing': standing,
        'registration_number': result.student.registration_number,
        'student_name': result.student.user.username,
        'result_status': result.status,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.enter_marks')])
def compute_offering_grades(request, offering_id):
    try:
        offering = CourseOffering.objects.select_related('faculty', 'course', 'semester').get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.user_type == 'teacher':
        faculty = _get_faculty(request.user)
        if not faculty or offering.faculty_id != faculty.faculty_id:
            return Response({'error': 'You can only compute grades for your own courses.'}, status=status.HTTP_403_FORBIDDEN)

    stats = _compute_offering_final_grades(offering)
    return Response({'message': 'Final grades computed.', **stats})


@api_view(['POST'])
@permission_classes([IsAdmin])
def unlock_offering_marks(request, offering_id):
    """Grant temporary marks edit access or unlock course marks until a datetime."""
    try:
        offering = CourseOffering.objects.get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        duration = parse_unlock_duration(request.data, default_hours=24, default_minutes=0)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    faculty_id = request.data.get('faculty_id')
    student_id = request.data.get('student_id')
    exam_id = request.data.get('exam_id')
    reason = request.data.get('reason', '')

    offering.marks_locked = True
    offering.marks_unlock_until = timezone.now() + duration
    offering.save(update_fields=['marks_locked', 'marks_unlock_until'])

    if faculty_id:
        from faculty.models import Faculty
        faculty = Faculty.objects.filter(faculty_id=faculty_id).first()
        if faculty and student_id:
            MarksEditPermission.objects.create(
                offering=offering,
                student_id=student_id,
                examination_id=exam_id,
                granted_by=request.user,
                granted_to=faculty,
                expires_at=offering.marks_unlock_until,
                reason=reason,
                request_status='approved',
                is_active=True,
                reviewed_at=timezone.now(),
            )

    log_audit(request, 'unlock_marks', 'course_offering', offering.offering_id, new_value={
        'duration': format_unlock_duration(duration), 'student_id': student_id,
    })
    return Response({
        'message': f'Course marks unlocked for {format_unlock_duration(duration)}.',
        'marks_unlock_until': offering.marks_unlock_until,
        'marks_locked': offering.marks_locked,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def lock_offering_marks(request, offering_id):
    """Re-lock course marks and clear bulk unlock window."""
    try:
        offering = CourseOffering.objects.get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    offering.marks_locked = True
    offering.marks_unlock_until = None
    offering.save(update_fields=['marks_locked', 'marks_unlock_until'])

    MarksEditPermission.objects.filter(
        offering=offering,
        request_status='approved',
        is_active=True,
    ).update(is_active=False)

    log_audit(request, 'lock_marks', 'course_offering', offering.offering_id)
    return Response({
        'message': 'Course marks locked.',
        'marks_locked': True,
    })


def _publish_single_result(result, performed_by):
    """Publish one result and run promotion. Returns outcome dict."""
    from enrollments.promotion import promote_student_after_published_result
    from academics.policy_utils import apply_standing_after_publish

    if result.is_published:
        return {
            'student_id': result.student_id,
            'registration_number': result.student.registration_number,
            'student_name': result.student.user.username,
            'result_status': result.status,
            'already_published': True,
            'promotion': {'promoted': False, 'reason': 'Result already published.'},
            'standing': {},
        }

    result.is_published = True
    result.published_date = timezone.now().date()
    result.published_by = performed_by
    result.save(update_fields=['is_published', 'published_date', 'published_by'])
    _sync_student_cgpa(result.student)

    standing = apply_standing_after_publish(
        result.student, result, performed_by=performed_by,
    )
    promo = promote_student_after_published_result(
        result.student, result.semester, performed_by=performed_by,
    )
    return {
        'student_id': result.student_id,
        'registration_number': result.student.registration_number,
        'student_name': result.student.user.username,
        'result_status': result.status,
        'promotion': promo,
        'standing': standing,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.publish_results')])
def publish_semester_results(request):
    """Publish all approved, unpublished results for a semester."""
    semester_id = request.data.get('semester_id')
    if not semester_id:
        return Response({'error': 'semester_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    approved_result_ids = ResultApproval.objects.values_list('result_id', flat=True)
    results = Result.objects.select_related(
        'student', 'student__user', 'semester',
    ).filter(
        semester_id=semester_id,
        is_published=False,
        result_id__in=approved_result_ids,
    )

    summary = {
        'published_count': 0,
        'promoted': [],
        'held_back': [],
        'graduated': [],
        'graduation_blocked': [],
        'dismissal_review': [],
        'skipped': [],
    }

    for result in results:
        try:
            outcome = _publish_single_result(result, request.user)
            summary['published_count'] += 1
            promo = outcome['promotion']
            standing = outcome.get('standing') or {}
            entry = {
                'registration_number': outcome['registration_number'],
                'student_name': outcome['student_name'],
                'result_status': outcome['result_status'],
                'reason': promo.get('reason', ''),
            }
            if standing.get('academic_review_required'):
                summary['dismissal_review'].append({
                    **entry,
                    'consecutive_probation_count': standing.get('consecutive_probation_count'),
                })
            if promo.get('graduated'):
                summary['graduated'].append(entry)
            elif promo.get('graduation_blocked'):
                audit = promo.get('audit') or {}
                summary['graduation_blocked'].append({
                    **entry,
                    'audit_issues': audit.get('issues', []),
                })
            elif promo.get('promoted'):
                summary['promoted'].append(entry)
            elif not promo.get('graduated'):
                summary['held_back'].append(entry)
        except Exception as exc:
            summary['skipped'].append({
                'registration_number': result.student.registration_number,
                'error': str(exc),
            })

    log_audit(request, 'publish_semester_results', 'semester', semester_id, new_value=summary)
    return Response({
        'message': f'Published {summary["published_count"]} result(s).',
        **summary,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_any_permission(
    'examinations.view_examination', 'examinations.create_examination',
    'examinations.enter_marks', 'examinations.view_marks',
)])
def request_marks_edit(request):
    if not user_has_permission(request.user, 'examinations.request_marks_edit'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    faculty = _get_faculty(request.user)
    if not faculty:
        return Response({'error': 'Faculty profile required.'}, status=status.HTTP_403_FORBIDDEN)

    offering_id = request.data.get('offering_id', request.data.get('section_id'))
    student_id = request.data.get('student_id')
    exam_id = request.data.get('exam_id')
    reason = request.data.get('reason', '')
    try:
        duration = parse_unlock_duration(request.data, default_hours=48, default_minutes=0)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if not offering_id or not student_id or not exam_id:
        return Response({'error': 'offering_id, student_id, and exam_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        offering = CourseOffering.objects.get(offering_id=offering_id, faculty=faculty)
        student = Student.objects.get(student_id=student_id)
        exam = Examination.objects.select_related('exam_type', 'semester').get(exam_id=exam_id, offering=offering)
    except (CourseOffering.DoesNotExist, Student.DoesNotExist, Examination.DoesNotExist):
        return Response({'error': 'Invalid offering, student, or exam.'}, status=status.HTTP_404_NOT_FOUND)

    allowed, lock_reason = can_edit_exam_marks(exam, request.user, student_id)
    if allowed:
        return Response({'error': 'Marks are already editable for this student and exam.'}, status=status.HTTP_400_BAD_REQUEST)

    if MarksEditPermission.objects.filter(
        offering=offering, student=student, examination=exam,
        granted_to=faculty, request_status='pending',
    ).exists():
        return Response({'error': 'A pending request already exists for this student and exam.'}, status=status.HTTP_400_BAD_REQUEST)

    perm = MarksEditPermission.objects.create(
        offering=offering,
        student=student,
        examination=exam,
        granted_by=request.user,
        granted_to=faculty,
        expires_at=timezone.now() + duration,
        reason=reason or lock_reason,
        request_status='pending',
        is_active=False,
    )
    log_audit(request, 'request_marks_edit', 'marks_edit_permission', perm.permission_id, new_value={
        'student_id': student_id, 'exam_id': exam_id,
    })
    return Response(MarksEditPermissionSerializer(perm).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_marks_edit_requests(request):
    qs = MarksEditPermission.objects.select_related(
        'offering', 'offering__course', 'student', 'student__user',
        'granted_to', 'granted_to__user', 'examination',
    ).order_by('-created_at')
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(request_status=status_filter)
    return Response(MarksEditPermissionSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def review_marks_edit_request(request, permission_id):
    if not user_has_permission(request.user, 'examinations.approve_marks_edit'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        perm = MarksEditPermission.objects.select_related('offering', 'student').get(permission_id=permission_id)
    except MarksEditPermission.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    action = request.data.get('action')
    if action not in ('approve', 'reject'):
        return Response({'error': 'action must be approve or reject.'}, status=status.HTTP_400_BAD_REQUEST)

    if perm.request_status != 'pending':
        return Response({'error': 'Request already reviewed.'}, status=status.HTTP_400_BAD_REQUEST)

    perm.review_notes = request.data.get('review_notes', '')
    perm.reviewed_at = timezone.now()
    if action == 'approve':
        raw_hours = request.data.get('hours')
        raw_minutes = request.data.get('minutes')
        if raw_hours not in (None, '') or raw_minutes not in (None, ''):
            try:
                duration = parse_unlock_duration(request.data, default_hours=0, default_minutes=0)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            perm.expires_at = timezone.now() + duration
        elif perm.expires_at <= timezone.now():
            perm.expires_at = timezone.now() + parse_unlock_duration(
                {}, default_hours=48, default_minutes=0,
            )
        perm.request_status = 'approved'
        perm.is_active = True
    else:
        perm.request_status = 'rejected'
        perm.is_active = False
    perm.save()
    log_audit(request, f'{action}_marks_edit', 'marks_edit_permission', perm.permission_id)
    return Response(MarksEditPermissionSerializer(perm).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def revoke_marks_edit_request(request, permission_id):
    """Revoke an active marks edit permission before it expires."""
    try:
        perm = MarksEditPermission.objects.get(permission_id=permission_id)
    except MarksEditPermission.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not perm.is_active:
        return Response({'error': 'Permission is not active.'}, status=status.HTTP_400_BAD_REQUEST)

    perm.is_active = False
    perm.save(update_fields=['is_active'])
    log_audit(request, 'revoke_marks_edit', 'marks_edit_permission', perm.permission_id)
    return Response({
        'message': 'Marks edit access revoked.',
        'permission_id': perm.permission_id,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.create_examination')])
def create_continuous_assessment(request):
    """Teacher adds quiz, assignment, or presentation (max 10% each, 30% total continuous)."""
    if request.user.user_type != 'teacher':
        return Response({'error': 'Teachers only.'}, status=status.HTTP_403_FORBIDDEN)
    faculty = _get_faculty(request.user)
    if not faculty:
        return Response({'error': 'Faculty profile required.'}, status=status.HTTP_403_FORBIDDEN)

    offering_id = request.data.get('offering_id')
    exam_name = (request.data.get('exam_name') or '').strip()
    weight = request.data.get('weight_percentage')
    total_marks = request.data.get('total_marks', 100)
    category = (request.data.get('assessment_category') or 'quiz').strip().lower()

    if category not in CATEGORY_WEIGHT_CAP:
        return Response(
            {'error': 'assessment_category must be quiz, assignment, or presentation.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not offering_id or not exam_name or weight is None:
        return Response(
            {'error': 'offering_id, exam_name, assessment_category, and weight_percentage are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        offering = CourseOffering.objects.select_related('course', 'semester').get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if offering.faculty_id != faculty.faculty_id:
        return Response({'error': 'You can only manage your own courses.'}, status=status.HTTP_403_FORBIDDEN)
    if offering_submission_locked(offering):
        return Response({'error': 'Course marks are locked. Request an edit from admin first.'}, status=status.HTTP_403_FORBIDDEN)

    weight_dec = Decimal(str(weight))
    cap = CATEGORY_WEIGHT_CAP[category]
    if weight_dec <= 0 or weight_dec > cap:
        return Response({'error': f'weight_percentage must be between 0 and {cap} for {category}.'}, status=status.HTTP_400_BAD_REQUEST)

    used = _category_weight_used(offering, category)
    if used + weight_dec > cap:
        return Response(
            {'error': f'{category.title()} assessments cannot exceed {cap}% (currently {used}%, requested {weight_dec}%).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    continuous_total = sum(_category_weight_used(offering, c) for c in CATEGORY_WEIGHT_CAP) + weight_dec
    if continuous_total > Decimal('30'):
        return Response(
            {'error': f'Total continuous weight cannot exceed 30% (would be {continuous_total}%).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .marks_locking import PERIOD_PRE_MID

    marks_period = PERIOD_PRE_MID

    exam_type = ExamType.objects.filter(marks_period=marks_period).first()
    if not exam_type:
        exam_type = ExamType.objects.create(
            type_name='Continuous Assessment' if marks_period == PERIOD_PRE_MID else 'Post-Mid Assessment',
            weightage_percentage=Decimal('30') if marks_period == PERIOD_PRE_MID else Decimal('20'),
            marks_period=marks_period,
        )

    exam = Examination.objects.create(
        course=offering.course,
        semester=offering.semester,
        offering=offering,
        exam_type=exam_type,
        assessment_category=category,
        exam_name=exam_name,
        exam_date=timezone.now().date(),
        total_marks=Decimal(str(total_marks)),
        passing_marks=Decimal(str(total_marks)) / Decimal('2'),
        weight_percentage=weight_dec,
        created_by=request.user,
    )
    return Response(ExaminationSerializer(exam).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def offering_marks_edit_requests(request):
    if request.method == 'GET':
        if not user_has_permission(request.user, 'examinations.approve_marks_edit') and request.user.user_type != 'admin':
            if request.user.user_type != 'teacher':
                return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            faculty = _get_faculty(request.user)
            qs = OfferingMarksEditRequest.objects.filter(faculty=faculty)
        else:
            qs = OfferingMarksEditRequest.objects.all()
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.select_related(
            'offering__course', 'offering__semester', 'faculty__user',
        ).order_by('-requested_at')
        return Response(OfferingMarksEditRequestSerializer(qs, many=True).data)

    if request.user.user_type != 'teacher':
        return Response({'error': 'Teachers only.'}, status=status.HTTP_403_FORBIDDEN)
    faculty = _get_faculty(request.user)
    offering_id = request.data.get('offering_id')
    reason = (request.data.get('reason') or '').strip()
    if not offering_id or not reason:
        return Response({'error': 'offering_id and reason are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        offering = CourseOffering.objects.get(offering_id=offering_id, faculty=faculty)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Completed course not found for your account.'}, status=status.HTTP_404_NOT_FOUND)

    if not offering_submission_locked(offering):
        return Response({'error': 'Marks are not locked yet — edit directly without a request.'}, status=status.HTTP_400_BAD_REQUEST)

    if OfferingMarksEditRequest.objects.filter(offering=offering, status='pending').exists():
        return Response({'error': 'A pending request already exists for this course.'}, status=status.HTTP_400_BAD_REQUEST)

    req = OfferingMarksEditRequest.objects.create(
        offering=offering, faculty=faculty, reason=reason,
    )

    from notifications.models import Notification, NotificationType
    from accounts.models import User
    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='Academic', defaults={'description': 'Academic updates'},
    )
    for admin in User.objects.filter(user_type='admin', is_active=True):
        Notification.objects.create(
            notification_type=notif_type,
            recipient=admin,
            title='Teacher marks edit request',
            message=(
                f'{faculty.user.username} requested marks edit for '
                f'{offering.course.course_code}. Reason: {reason}'
            ),
            priority='high',
        )

    return Response(OfferingMarksEditRequestSerializer(req).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def review_offering_marks_edit_request(request, request_id):
    if not user_has_permission(request.user, 'examinations.approve_marks_edit') and request.user.user_type != 'admin':
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    action = request.data.get('action')
    remarks = (request.data.get('remarks') or '').strip()
    if action not in ('approve', 'reject'):
        return Response({'error': 'action must be approve or reject.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        edit_req = OfferingMarksEditRequest.objects.select_related(
            'offering', 'offering__course', 'faculty__user',
        ).get(request_id=request_id)
    except OfferingMarksEditRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if edit_req.status != 'pending':
        return Response({'error': 'Request already reviewed.'}, status=status.HTTP_400_BAD_REQUEST)

    edit_req.status = 'approved' if action == 'approve' else 'rejected'
    edit_req.reviewed_by = request.user
    edit_req.reviewed_at = timezone.now()
    edit_req.admin_remarks = remarks
    edit_req.save()

    if action == 'approve':
        offering = edit_req.offering
        raw_hours = request.data.get('hours')
        raw_minutes = request.data.get('minutes')
        if raw_hours not in (None, '') or raw_minutes not in (None, ''):
            try:
                duration = parse_unlock_duration(request.data, default_hours=0, default_minutes=0)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            offering.marks_unlock_until = timezone.now() + duration
        else:
            offering.marks_unlock_until = timezone.now() + parse_unlock_duration(
                {}, default_hours=48, default_minutes=0,
            )
        offering.marks_locked = True
        offering.save(update_fields=['marks_locked', 'marks_unlock_until'])

    from notifications.models import Notification, NotificationType
    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='Academic', defaults={'description': 'Academic updates'},
    )
    msg = (
        f'Marks edit approved for {edit_req.offering.course.course_code}. '
        'Re-submit final marks when done.'
        if action == 'approve' else
        f'Marks edit rejected for {edit_req.offering.course.course_code}.'
    )
    Notification.objects.create(
        notification_type=notif_type,
        recipient=edit_req.faculty.user,
        title='Marks edit decision',
        message=msg + (f' {remarks}' if remarks else ''),
        priority='high',
    )

    return Response({
        'message': f'Request {edit_req.status}.',
        'request': OfferingMarksEditRequestSerializer(edit_req).data,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def approve_result(request, result_id):
    try:
        result = Result.objects.get(result_id=result_id)
    except Result.DoesNotExist:
        return Response({'error': 'Result not found.'}, status=status.HTTP_404_NOT_FOUND)

    if hasattr(result, 'approval'):
        return Response({'error': 'Result already approved.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ResultApprovalSerializer(data={
        'result': result.result_id,
        'approved_by': request.user.pk,
        'remarks': request.data.get('remarks', '')
    })
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)