from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.permissions import IsAdminOrTeacher, IsSuperuser, require_permission
from accounts.access_helpers import can_view_offering_roster, get_faculty_profile
from .models import CourseOffering
from .offering_serializers import (
    CourseOfferingSerializer,
    CourseOfferingCreateSerializer,
)
from enrollments.models import CourseRegistration


def _enrich_teacher_offering_row(data, assignment=None, offering=None):
    """Add program/department context and display labels for teacher dashboards."""
    if assignment:
        course = assignment.course
        program = assignment.program
        data['program_code'] = program.program_code
        data['program_name'] = program.program_name
        data['department_name'] = course.department.department_name
        data['department_id'] = course.department_id
    if offering is not None:
        from enrollments.repeat_utils import offering_teaching_complete
        data['teaching_complete'] = offering_teaching_complete(offering)
    repeat = bool(data.get('repeat_offering'))
    kind = 'Repeat' if repeat else 'Regular'
    data['offering_type_label'] = kind
    code = data.get('course_code') or ''
    name = data.get('course_name') or ''
    data['display_label'] = data.get('display_label') or f'{code} — {name} ({kind})'
    return data


def _filter_teacher_rows(rows, dept_id, program_id):
    if dept_id:
        try:
            dept_id = int(dept_id)
            rows = [r for r in rows if r.get('department_id') == dept_id]
        except (TypeError, ValueError):
            pass
    if program_id:
        try:
            program_id = int(program_id)
            from academics.models import DegreeProgram
            prog = DegreeProgram.objects.filter(program_id=program_id).first()
            if prog:
                rows = [r for r in rows if r.get('program_code') == prog.program_code]
        except (TypeError, ValueError):
            pass
    return rows


def _assignment_by_course(assignments):
    mapping = {}
    for assignment in assignments:
        mapping.setdefault(assignment.course_id, assignment)
    return mapping


def _build_completed_teacher_rows(assignments, offerings_qs):
    """Completed tab: only offerings with submitted (locked) final marks."""
    assignment_map = _assignment_by_course(assignments)
    rows = []
    for offering in offerings_qs.order_by('course__course_code', 'repeat_offering'):
        data = CourseOfferingSerializer(offering).data
        _enrich_teacher_offering_row(data, assignment_map.get(offering.course_id), offering)
        data['has_offering'] = True
        rows.append(data)
    return rows


def _build_active_teacher_rows(assignments, offerings_qs, completed_keys=None):
    """Active tab: live offerings plus assigned courses awaiting first enrollment."""
    from academics.session_utils import curriculum_semester_for_course, format_curriculum_semester

    completed_keys = completed_keys or set()

    offering_by_key = {(o.course_id, o.repeat_offering): o for o in offerings_qs}
    rows = []
    seen_keys = set()

    for assignment in assignments.order_by('program__program_code', 'course__course_code'):
        course = assignment.course
        program = assignment.program
        for repeat_flag in (False, True):
            offering = offering_by_key.get((course.course_id, repeat_flag))
            if repeat_flag and not offering:
                continue
            key = (course.course_id, repeat_flag)
            if key in seen_keys or key in completed_keys:
                continue
            if offering:
                data = CourseOfferingSerializer(offering).data
                _enrich_teacher_offering_row(data, assignment, offering)
                data['has_offering'] = True
            else:
                course_sem = curriculum_semester_for_course(program, course) if program else None
                label = format_curriculum_semester(course_sem)
                kind = 'Repeat' if repeat_flag else 'Regular'
                data = {
                    'offering_id': None,
                    'section_id': None,
                    'course_id': course.course_id,
                    'course_code': course.course_code,
                    'course_name': course.course_name,
                    'curriculum_semester': course_sem,
                    'repeat_offering': repeat_flag,
                    'semester_name': f'{label} ({kind})' if repeat_flag else label,
                    'semester_label': f'{label} ({kind})' if repeat_flag else label,
                    'enrolled_count': 0,
                    'is_active': True,
                    'marks_locked': False,
                    'has_offering': False,
                    'offering_type_label': kind,
                    'display_label': f'{course.course_code} — {course.course_name} ({kind})',
                }
                _enrich_teacher_offering_row(data, assignment)
            rows.append(data)
            seen_keys.add(key)

    for offering in offerings_qs:
        key = (offering.course_id, offering.repeat_offering)
        if key not in seen_keys:
            data = CourseOfferingSerializer(offering).data
            _enrich_teacher_offering_row(data, None, offering)
            data['has_offering'] = True
            rows.append(data)
            seen_keys.add(key)

    return rows


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_offerings(request):
    offerings = CourseOffering.objects.select_related('course', 'semester', 'faculty__user')
    if request.query_params.get('all') != '1':
        offerings = offerings.filter(is_active=True)
    semester = request.query_params.get('semester')
    course = request.query_params.get('course')
    faculty = request.query_params.get('faculty')
    if semester:
        offerings = offerings.filter(semester__semester_id=semester)
    if course:
        offerings = offerings.filter(course__course_id=course)
    if faculty:
        offerings = offerings.filter(faculty__faculty_id=faculty)
    curriculum_sem = request.query_params.get('curriculum_semester')
    if curriculum_sem:
        try:
            offerings = offerings.filter(curriculum_semester=int(curriculum_sem))
        except (TypeError, ValueError):
            pass
    return Response(CourseOfferingSerializer(offerings, many=True).data)


OFFERING_MANUAL_MSG = (
    'Course offerings are created automatically when students enroll '
    '(after Teacher Course Management assigns faculty). Manual API access is superuser-only.'
)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuperuser])
def create_offering(request):
    serializer = CourseOfferingCreateSerializer(data=request.data)
    if serializer.is_valid():
        offering = serializer.save()
        offering = CourseOffering.objects.select_related('course', 'semester').get(pk=offering.pk)
        from examinations.assessment_setup import ensure_offering_assessments
        assessment_result = ensure_offering_assessments(offering, created_by=request.user)
        data = CourseOfferingSerializer(offering).data
        data['assessments'] = assessment_result
        return Response(data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminOrTeacher])
def offering_detail(request, offering_id):
    try:
        offering = CourseOffering.objects.select_related(
            'course', 'semester', 'faculty__user',
        ).get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(CourseOfferingSerializer(offering).data)

    if request.method == 'PUT':
        if not request.user.is_superuser:
            return Response({'error': OFFERING_MANUAL_MSG}, status=status.HTTP_403_FORBIDDEN)
        serializer = CourseOfferingCreateSerializer(offering, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(CourseOfferingSerializer(offering).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        if not request.user.is_superuser:
            return Response({'error': OFFERING_MANUAL_MSG}, status=status.HTTP_403_FORBIDDEN)
        offering.is_active = False
        offering.save(update_fields=['is_active'])
        return Response({'message': 'Course offering deactivated.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_offerings(request):
    """Teacher courses: assigned program courses, with or without enrolled students."""
    if request.user.user_type != 'teacher':
        return Response({'error': 'Only teachers can access this.'}, status=status.HTTP_403_FORBIDDEN)

    from faculty.models import Faculty, FacultyCourseAssignment

    try:
        faculty = Faculty.objects.get(user=request.user)
    except Faculty.DoesNotExist:
        return Response({'error': 'Faculty profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.query_params.get('marks_eligible') == '1':
        from examinations.marks_locking import (
            offering_bulk_unlock_active,
            offering_teacher_marks_eligible,
        )
        from enrollments.repeat_utils import roster_eligible_count, sync_offering_enrolled_count, offering_is_empty_shell

        assignments = FacultyCourseAssignment.objects.filter(
            faculty=faculty, is_active=True,
        ).select_related('course', 'course__department', 'program')
        assignment_map = _assignment_by_course(assignments)

        eligible_offerings = CourseOffering.objects.filter(
            faculty=faculty, is_active=True,
        ).select_related('course', 'semester', 'course__department').order_by(
            'course__course_code', 'repeat_offering',
        )

        rows = []
        for offering in eligible_offerings:
            if not offering_teacher_marks_eligible(offering):
                continue
            sync_offering_enrolled_count(offering)
            if offering_is_empty_shell(offering):
                continue
            if roster_eligible_count(offering) == 0 and not offering_bulk_unlock_active(offering):
                continue
            data = CourseOfferingSerializer(offering).data
            _enrich_teacher_offering_row(data, assignment_map.get(offering.course_id), offering)
            data['has_offering'] = True
            rows.append(data)

        dept_id = request.query_params.get('department_id')
        program_id = request.query_params.get('program_id')
        return Response(_filter_teacher_rows(rows, dept_id, program_id))

    active_only = request.query_params.get('active', 'true')

    assignments = FacultyCourseAssignment.objects.filter(
        faculty=faculty, is_active=True,
    ).select_related('course', 'course__department', 'program', 'program__department')

    from enrollments.repeat_utils import (
        offering_teaching_complete,
        sync_offering_enrolled_count,
        offering_is_empty_shell,
        roster_eligible_count,
    )

    offerings_qs = CourseOffering.objects.filter(faculty=faculty).select_related(
        'course', 'semester', 'course__department',
    )
    if active_only == 'false':
        complete_ids = [
            o.pk for o in offerings_qs
            if offering_teaching_complete(o)
        ]
        offerings_qs = offerings_qs.filter(pk__in=complete_ids)
        completed_keys = set()
    elif active_only == 'true':
        all_teacher_offerings = CourseOffering.objects.filter(
            faculty=faculty, is_active=True,
        ).select_related('course', 'semester', 'course__department')
        completed_keys = {
            (o.course_id, o.repeat_offering)
            for o in all_teacher_offerings
            if offering_teaching_complete(o)
        }
        offerings_qs = all_teacher_offerings
        active_ids = [
            o.pk for o in offerings_qs
            if not offering_teaching_complete(o) and not offering_is_empty_shell(o)
        ]
        offerings_qs = offerings_qs.filter(pk__in=active_ids)
    else:
        offerings_qs = offerings_qs.filter(is_active=True)
        completed_keys = set()

    for offering in offerings_qs:
        sync_offering_enrolled_count(offering)

    if active_only == 'false':
        rows = _build_completed_teacher_rows(assignments, offerings_qs)
    else:
        rows = _build_active_teacher_rows(assignments, offerings_qs, completed_keys)

    dept_id = request.query_params.get('department_id')
    program_id = request.query_params.get('program_id')
    return Response(_filter_teacher_rows(rows, dept_id, program_id))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_offering_students(request, offering_id):
    try:
        offering = CourseOffering.objects.select_related('faculty').get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_offering_roster(request.user, offering):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    attendance_date = request.query_params.get('attendance_date')
    for_marks = request.query_params.get('for_marks') in ('1', 'true', 'yes')

    from enrollments.repeat_utils import roster_eligible_registrations

    registrations = roster_eligible_registrations(offering).select_related('student__user')
    approved_leave_ids = set()
    if attendance_date:
        from attendance.models import LeaveApplication
        approved_leave_ids = set(
            LeaveApplication.objects.filter(
                offering_id=offering_id,
                status='approved',
                start_date__lte=attendance_date,
                end_date__gte=attendance_date,
            ).values_list('student_id', flat=True)
        )
    data = []
    for reg in registrations:
        on_approved_leave = reg.student.student_id in approved_leave_ids
        data.append({
            'registration_id': reg.registration_id,
            'student_id': reg.student.student_id,
            'registration_number': reg.student.registration_number,
            'username': reg.student.user.username,
            'email': reg.student.user.email,
            'approved_leave': on_approved_leave,
            'default_status': 'leave' if on_approved_leave else 'present',
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('examinations.enter_marks')])
def submit_final_marks(request, offering_id):
    try:
        offering = CourseOffering.objects.select_related('faculty').get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.user_type == 'teacher':
        if not offering.faculty_id or offering.faculty.user_id != request.user.user_id:
            return Response({'error': 'You can only submit marks for your own courses.'}, status=status.HTTP_403_FORBIDDEN)

    from examinations.models import Marks, OfferingMarksEditRequest
    from examinations.results_pipeline import compute_offering_final_grades, refresh_students_after_offering_grades
    from examinations.assessment_setup import (
        get_offering_weight_allocation_status,
        get_promotion_relevant_examinations,
    )

    weight_status = get_offering_weight_allocation_status(offering)
    if not weight_status['weight_complete']:
        return Response(
            {
                'error': (
                    f'Assessment weights must total 100% before submitting final marks '
                    f'(currently {weight_status["total_allocated"]:.0f}%). '
                    'Complete quiz, assignment, presentation (30%), mid (30%), and final (40%) in Step 2.'
                ),
                'weight_status': weight_status,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    from enrollments.repeat_utils import roster_eligible_registrations

    regs = roster_eligible_registrations(offering).select_related('student')
    missing = []
    exams = get_promotion_relevant_examinations(offering)
    for reg in regs:
        for exam in exams:
            if not Marks.objects.filter(exam=exam, student=reg.student).exists():
                missing.append(f'{reg.student.registration_number} — {exam.exam_name}')
    if missing:
        return Response(
            {
                'error': 'Cannot submit final marks — missing entries for some students/exams.',
                'missing': missing[:20],
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    grade_stats = compute_offering_final_grades(offering)

    gpa_stats = refresh_students_after_offering_grades(offering)

    offering.marks_locked = True
    offering.marks_unlock_until = None
    offering.save(update_fields=['marks_locked', 'marks_unlock_until'])

    OfferingMarksEditRequest.objects.filter(
        offering=offering, status='approved',
    ).update(status='rejected', admin_remarks='Closed — teacher re-submitted final marks.')

    return Response({
        'message': 'Final marks submitted. Course marks are now locked.',
        'offering_id': offering_id,
        **grade_stats,
        **gpa_stats,
    })
