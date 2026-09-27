from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.permissions import IsAdmin
from enrollments.models import CourseRegistration
from .models import Student, StudentProfile
from .serializers import StudentSerializer, StudentCreateSerializer, StudentProfileSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_student_profile(request):
    if request.user.user_type != 'student':
        return Response(
            {'error': 'Only student accounts can access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        student = Student.objects.select_related('user', 'program', 'profile').get(user=request.user)
        return Response(StudentSerializer(student).data)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found for this account.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_students(request):
    students = Student.objects.select_related('user', 'program', 'program__department').all()
    status_filter = request.query_params.get('status')
    if status_filter:
        students = students.filter(status=status_filter)
    dept = request.query_params.get('department')
    if dept:
        students = students.filter(program__department__department_id=dept)
    program = request.query_params.get('program')
    if program:
        students = students.filter(program__program_id=program)

    data = StudentSerializer(students, many=True).data
    return Response({
        'count': len(data),
        'students': data,
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def get_student(request, student_id):
    try:
        student = Student.objects.select_related(
            'user', 'program', 'program__department', 'profile', 'applicant'
        ).get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    payload = StudentSerializer(student).data
    payload['department_name'] = student.program.department.department_name
    if student.applicant_id:
        from admissions.models import ApplicantDocument, AcademicRecord
        from admissions.serializers import ApplicantDocumentSerializer, AcademicRecordSerializer
        payload['applicant_documents'] = ApplicantDocumentSerializer(
            ApplicantDocument.objects.filter(applicant=student.applicant), many=True
        ).data
        payload['academic_records'] = AcademicRecordSerializer(
            AcademicRecord.objects.filter(applicant=student.applicant), many=True
        ).data
        payload['applicant_profile'] = {
            'first_name': student.applicant.first_name,
            'last_name': student.applicant.last_name,
            'cnic': student.applicant.cnic,
            'phone': student.applicant.phone,
            'email': student.user.email,
        }
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_download_student_document(request, student_id, doc_id):
    from django.core.files.storage import default_storage
    from django.http import FileResponse, Http404
    from admissions.models import ApplicantDocument

    try:
        student = Student.objects.select_related('applicant').get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not student.applicant_id:
        return Response({'error': 'No applicant documents for this student.'}, status=status.HTTP_404_NOT_FOUND)
    try:
        document = ApplicantDocument.objects.get(document_id=doc_id, applicant=student.applicant)
    except ApplicantDocument.DoesNotExist:
        return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
    if default_storage.exists(document.file_path):
        file = default_storage.open(document.file_path, 'rb')
        response = FileResponse(file, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        return response
    raise Http404('File not found')


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdmin])
def admin_update_student_profile(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        profile, _ = StudentProfile.objects.get_or_create(student=student)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    allowed = {
        'blood_group', 'medical_conditions', 'disabilities', 'guardian_name',
        'guardian_cnic', 'guardian_phone', 'guardian_occupation',
        'residential_address', 'permanent_address',
        'permanent_address_same_as_residential', 'profile_locked',
    }
    data = {k: v for k, v in request.data.items() if k in allowed}
    serializer = StudentProfileSerializer(profile, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_degree_progress(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.select_related('program').get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    from academics.models import ProgramCourse
    curriculum = ProgramCourse.objects.filter(program=student.program).select_related('course')
    total_courses = curriculum.count()
    total_credits = sum(pc.course.credit_hours for pc in curriculum)

    completed_regs = CourseRegistration.objects.filter(
        student=student, status='completed',
    ).select_related('course')
    completed_course_ids = set(completed_regs.values_list('course_id', flat=True))
    completed_courses = len(completed_course_ids)
    earned_credits = sum(r.course.credit_hours for r in completed_regs)

    by_semester = {}
    for pc in curriculum.order_by('semester_number'):
        sem = pc.semester_number
        if sem not in by_semester:
            by_semester[sem] = {'total': 0, 'completed': 0, 'courses': []}
        done = pc.course_id in completed_course_ids
        by_semester[sem]['total'] += 1
        if done:
            by_semester[sem]['completed'] += 1
        by_semester[sem]['courses'].append({
            'course_code': pc.course.course_code,
            'course_name': pc.course.course_name,
            'credit_hours': pc.course.credit_hours,
            'completed': done,
        })

    pct = round((earned_credits / total_credits) * 100, 1) if total_credits else 0
    from .degree_audit import run_degree_audit
    audit = run_degree_audit(student)
    return Response({
        'registration_number': student.registration_number,
        'program': student.program.program_name,
        'current_semester': student.current_semester,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'total_credit_hours': total_credits,
        'earned_credit_hours': earned_credits,
        'degree_completion_percent': pct,
        'semester_breakdown': by_semester,
        'graduation_eligible': audit['eligible'],
        'graduation_issues': audit['issues'],
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_student(request):
    serializer = StudentCreateSerializer(data=request.data)
    if serializer.is_valid():
        program    = serializer.validated_data['program']
        batch_year = serializer.validated_data['batch_year']

        count = Student.objects.filter(program=program, batch_year=batch_year).count() + 1
        registration_number = f"{program.program_code}-{batch_year}-{str(count).zfill(4)}"

        student = serializer.save(registration_number=registration_number)
        StudentProfile.objects.create(student=student)

        return Response(StudentSerializer(student).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_student_profile(request):
    if request.user.user_type != 'student':
        return Response(
            {'error': 'Only student accounts can access this endpoint.'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        student = Student.objects.get(user=request.user)
        profile, _ = StudentProfile.objects.get_or_create(student=student)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found for this account.'}, status=status.HTTP_404_NOT_FOUND)

    if profile.profile_locked:
        return Response(
            {'error': 'Your profile is locked. Contact the admin office to update details.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH', 'PUT'])
@permission_classes([IsAdmin])
def update_student_status(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    allowed_fields = {'status', 'current_semester'}
    data = {k: v for k, v in request.data.items() if k in allowed_fields}

    if not data:
        return Response(
            {'error': 'Only status and current_semester can be updated here.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    for field, value in data.items():
        setattr(student, field, value)
    student.save(update_fields=list(data.keys()))

    return Response(StudentSerializer(student).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def academic_standing(request):
    """Students with published results and academic standing flags."""
    from examinations.models import Result

    semester_id = request.query_params.get('semester_id')
    standing_filter = request.query_params.get('standing')

    if standing_filter == 'dismissal_review':
        flagged = Student.objects.filter(
            academic_review_required=True,
        ).select_related('user', 'program')
        if semester_id:
            flagged = flagged.filter(
                student_id__in=Result.objects.filter(
                    semester_id=semester_id, is_published=True,
                ).values_list('student_id', flat=True),
            )
        items = []
        for student in flagged.order_by('registration_number'):
            latest = Result.objects.filter(
                student=student, is_published=True,
            ).select_related('semester').order_by('-published_date').first()
            items.append({
                'student_id': student.student_id,
                'registration_number': student.registration_number,
                'student_name': student.user.username,
                'program_name': student.program.program_name,
                'current_semester': student.current_semester,
                'semester_name': latest.semester.semester_name if latest else '—',
                'semester_id': latest.semester_id if latest else None,
                'sgpa': str(latest.sgpa) if latest else '—',
                'cgpa': str(student.cgpa),
                'result_status': latest.status if latest else '—',
                'standing': 'dismissal_review',
                'student_status': student.status,
                'consecutive_probation_count': student.consecutive_probation_count,
                'academic_review_required': student.academic_review_required,
            })
        return Response({'count': len(items), 'students': items})

    results = Result.objects.filter(
        is_published=True,
    ).select_related('student', 'student__user', 'student__program', 'semester')

    if semester_id:
        results = results.filter(semester_id=semester_id)

    items = []
    for r in results.order_by('student__registration_number'):
        student = r.student
        if student.status == 'graduated':
            standing = 'graduated'
        elif student.academic_review_required:
            standing = 'dismissal_review'
        elif r.status == 'fail':
            standing = 'held_back'
        elif r.status == 'probation':
            standing = 'probation'
        else:
            standing = 'promoted'

        if standing_filter and standing != standing_filter:
            continue

        items.append({
            'student_id': student.student_id,
            'registration_number': student.registration_number,
            'student_name': student.user.username,
            'program_name': student.program.program_name,
            'current_semester': student.current_semester,
            'semester_name': r.semester.semester_name,
            'semester_id': r.semester_id,
            'sgpa': str(r.sgpa),
            'cgpa': str(r.cgpa),
            'result_status': r.status,
            'standing': standing,
            'student_status': student.status,
            'consecutive_probation_count': student.consecutive_probation_count,
            'academic_review_required': student.academic_review_required,
        })

    return Response({'count': len(items), 'students': items})


@api_view(['POST'])
@permission_classes([IsAdmin])
def manual_promote_student(request, student_id):
    """Admin override: promote student after reviewing a held-back case."""
    from academics.models import Semester
    from examinations.models import Result
    from enrollments.promotion import promote_student_after_published_result

    try:
        student = Student.objects.select_related('user', 'program').get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    semester_id = request.data.get('semester_id')
    if semester_id:
        try:
            semester = Semester.objects.get(semester_id=semester_id)
        except Semester.DoesNotExist:
            return Response({'error': 'Semester not found.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        latest = Result.objects.filter(
            student=student, is_published=True,
        ).select_related('semester').order_by('-published_date').first()
        if not latest:
            return Response({'error': 'No published result found.'}, status=status.HTTP_400_BAD_REQUEST)
        semester = latest.semester

    fail_result = Result.objects.filter(student=student, semester=semester, status='fail').first()
    if fail_result:
        fail_result.status = 'probation'
        fail_result.save(update_fields=['status'])

    published_result = Result.objects.filter(
        student=student, semester=semester, is_published=True,
    ).first()
    if published_result and published_result.promotion_applied:
        return Response(
            {'error': 'Promotion already applied for this semester result.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    promo = promote_student_after_published_result(student, semester, performed_by=request.user)
    student.refresh_from_db()
    return Response({
        'message': 'Promotion processed.',
        'promotion': promo,
        'student': StudentSerializer(student).data,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def repeat_semester(request, student_id):
    """Re-enroll student in their current curriculum semester (repeat year/term)."""
    from academics.models import Semester
    from enrollments.promotion import enroll_student_for_semester

    try:
        student = Student.objects.select_related('user', 'program').get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    semester = Semester.objects.filter(is_current=True).first()
    if not semester:
        return Response({'error': 'No current academic semester configured.'}, status=status.HTTP_400_BAD_REQUEST)

    enroll_stats = enroll_student_for_semester(student, semester, performed_by=request.user)
    return Response({
        'message': f'Student re-enrolled for curriculum semester {student.current_semester}.',
        **enroll_stats,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def confirm_dismissal(request, student_id):
    """Confirm academic dismissal after consecutive probation review."""
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not student.academic_review_required:
        return Response(
            {'error': 'Student is not flagged for dismissal review.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    student.status = 'expelled'
    student.academic_review_required = False
    student.save(update_fields=['status', 'academic_review_required'])
    return Response({
        'message': 'Student dismissed (expelled).',
        'student': StudentSerializer(student).data,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def clear_dismissal_review(request, student_id):
    """Allow student to continue — clear dismissal review flag."""
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    student.academic_review_required = False
    student.consecutive_probation_count = 0
    student.save(update_fields=['academic_review_required', 'consecutive_probation_count'])
    return Response({
        'message': 'Dismissal review cleared. Student may continue.',
        'student': StudentSerializer(student).data,
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_graduation_candidates(request):
    """Students near or at program completion who may be ready to graduate."""
    from .degree_audit import run_degree_audit

    students = Student.objects.filter(
        status='active',
    ).select_related('user', 'program')

    candidates = []
    for student in students.order_by('registration_number'):
        audit = run_degree_audit(student)
        if not (audit['curriculum_complete'] or audit['at_final_semester']):
            continue
        if audit['eligible']:
            bucket = 'ready'
        elif audit['curriculum_complete']:
            bucket = 'blocked'
        else:
            bucket = 'in_progress'
        candidates.append({
            'student_id': student.student_id,
            'registration_number': student.registration_number,
            'student_name': student.user.username,
            'program_name': student.program.program_name,
            'current_semester': student.current_semester,
            'cgpa': str(student.cgpa),
            'degree_completion_percent': audit['degree_completion_percent'],
            'eligible': audit['eligible'],
            'bucket': bucket,
            'issue_count': len(audit['issues']),
            'issues': audit['issues'][:3],
        })

    return Response({
        'count': len(candidates),
        'ready_count': sum(1 for c in candidates if c['bucket'] == 'ready'),
        'candidates': candidates,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def degree_audit_view(request, student_id=None):
    """Full degree audit — admin by student_id, student uses own profile."""
    from .degree_audit import run_degree_audit

    if student_id is not None:
        if request.user.user_type != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            student = Student.objects.select_related('user', 'program').get(student_id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        if request.user.user_type != 'student':
            return Response({'error': 'Only students can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            student = Student.objects.select_related('user', 'program').get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    audit = run_degree_audit(student)
    return Response({
        'student_id': student.student_id,
        'registration_number': student.registration_number,
        'student_name': student.user.username,
        'program_name': student.program.program_name,
        'status': student.status,
        **audit,
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def confirm_graduation(request, student_id):
    """Admin confirms graduation after degree audit passes."""
    from django.utils import timezone
    from notifications.models import Notification, NotificationType
    from .degree_audit import run_degree_audit, build_transcript

    try:
        student = Student.objects.select_related('user', 'program').get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    if student.status == 'graduated':
        return Response({'error': 'Student is already graduated.'}, status=status.HTTP_400_BAD_REQUEST)

    audit = run_degree_audit(student)
    if not audit['eligible']:
        return Response(
            {'error': 'Degree audit failed.', 'audit': audit},
            status=status.HTTP_400_BAD_REQUEST,
        )

    student.status = 'graduated'
    student.graduation_date = timezone.now().date()
    student.save(update_fields=['status', 'graduation_date'])

    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='Academic',
        defaults={'description': 'Academic updates'},
    )
    Notification.objects.create(
        notification_type=notif_type,
        recipient=student.user,
        title='Congratulations — Graduated!',
        message=(
            f'You have officially graduated from {student.program.program_name}. '
            f'Your transcript is now available as an official document.'
        ),
        priority='high',
    )

    return Response({
        'message': 'Graduation confirmed.',
        'student': StudentSerializer(student).data,
        'transcript': build_transcript(student),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transcript_view(request, student_id=None):
    """Transcript — admin by student_id; student views own."""
    from .degree_audit import build_transcript

    if student_id is not None:
        if request.user.user_type != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            student = Student.objects.select_related('user', 'program').get(student_id=student_id)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        try:
            student = Student.objects.select_related('user', 'program').get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(build_transcript(student))
