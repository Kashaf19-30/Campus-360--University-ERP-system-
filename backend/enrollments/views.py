from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Prefetch
from accounts.permissions import IsAdmin, IsStudent, require_permission
from academics.models import Semester, CourseOffering, ProgramCourse
from academics.display_utils import offering_teacher_name
from academics.prerequisite_utils import check_course_prerequisites
from students.models import Student
from examinations.models import FinalGrade
from fees.models import Challan
from notifications.models import Notification, NotificationType
from .models import Enrollment, CourseRegistration, RepeatCourseRequest
from .serializers import EnrollmentSerializer, CourseRegistrationSerializer, RepeatCourseRequestSerializer
from .promotion import (
    _semester_fee_paid, enroll_student_for_semester,
    get_student_semester_credit_summary, _registered_credit_hours,
)
from .repeat_utils import (
    reconcile_repeat_registrations,
    visible_registrations_for_student,
    eligible_failed_courses_for_repeat,
    failed_course_ids_for_repeat_request,
    enroll_approved_repeat_request,
    ensure_curriculum_enrolled_if_paid,
)
from academics.policy_utils import get_academic_policy


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_enrollments(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    reconcile_repeat_registrations(student)
    current_semester = Semester.objects.filter(is_current=True).first()
    ensure_curriculum_enrolled_if_paid(student, current_semester)
    visible_regs = visible_registrations_for_student(student, current_semester)
    visible_ids = [r.registration_id for r in visible_regs]
    reg_qs = CourseRegistration.objects.filter(
        registration_id__in=visible_ids,
    ).select_related(
        'course', 'student', 'student__program', 'offering', 'offering__faculty__user',
        'enrollment__semester',
    )
    enrollments = Enrollment.objects.select_related('semester').prefetch_related(
        Prefetch('course_registrations', queryset=reg_qs),
    ).filter(student=student)
    if current_semester:
        enrollments = enrollments.filter(semester=current_semester)
    return Response({
        'enrollments': EnrollmentSerializer(enrollments, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_enrollments(request):
    regs = CourseRegistration.objects.select_related(
        'student', 'student__user', 'student__program', 'student__program__department',
        'course', 'offering', 'offering__faculty__user', 'enrollment__semester',
    ).filter(status='registered')

    dept = request.query_params.get('department')
    if dept:
        regs = regs.filter(student__program__department__department_id=dept)
    program = request.query_params.get('program')
    if program:
        regs = regs.filter(student__program__program_id=program)
    course = request.query_params.get('course')
    if course:
        regs = regs.filter(course__course_id=course)
    curriculum_sem = request.query_params.get('curriculum_semester')
    if curriculum_sem:
        try:
            regs = regs.filter(student__current_semester=int(curriculum_sem))
        except (TypeError, ValueError):
            pass

    items = []
    seen_students = set()
    for reg in regs.order_by('student__registration_number', 'course__course_code'):
        seen_students.add(reg.student_id)
        items.append({
            'registration_id': reg.registration_id,
            'registration_number': reg.student.registration_number,
            'student_name': reg.student.user.username,
            'program_name': reg.student.program.program_name,
            'course_code': reg.course.course_code,
            'course_name': reg.course.course_name,
            'faculty_name': offering_teacher_name(reg.offering, default='—') if reg.offering_id else '—',
            'semester_name': reg.enrollment.semester.semester_name,
            'curriculum_semester': reg.student.current_semester,
            'status': reg.status,
            'credit_hours': reg.course.credit_hours,
        })

    if not course:
        enrollments = Enrollment.objects.select_related(
            'student', 'student__user', 'student__program', 'student__program__department',
            'semester',
        ).filter(status='enrolled')
        if dept:
            enrollments = enrollments.filter(student__program__department__department_id=dept)
        if program:
            enrollments = enrollments.filter(student__program__program_id=program)
        if curriculum_sem:
            try:
                enrollments = enrollments.filter(student__current_semester=int(curriculum_sem))
            except (TypeError, ValueError):
                pass

        for enr in enrollments.order_by('student__registration_number'):
            if enr.student_id in seen_students:
                continue
            if CourseRegistration.objects.filter(
                enrollment=enr, status='registered',
            ).exists():
                continue
            seen_students.add(enr.student_id)
            items.append({
                'registration_id': None,
                'registration_number': enr.student.registration_number,
                'student_name': enr.student.user.username,
                'program_name': enr.student.program.program_name,
                'course_code': '—',
                'course_name': 'Pending course assignment',
                'faculty_name': '—',
                'semester_name': enr.semester.semester_name,
                'curriculum_semester': enr.student.current_semester,
                'status': 'enrolled',
                'credit_hours': 0,
            })

    items.sort(key=lambda row: (
        row['registration_number'] or '',
        row['course_code'] if row['course_code'] != '—' else 'zzz',
    ))

    course_ids = {item['course_code'] for item in items if item['course_code'] != '—'}

    return Response({
        'stats': {
            'total_registrations': len(items),
            'unique_students': len(seen_students),
            'courses_count': len(course_ids),
        },
        'enrollments': items,
    })


def _notify_admins_repeat_request(student, courses, semester):
    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='Academic',
        defaults={'description': 'Academic updates'},
    )
    from accounts.models import User
    admins = User.objects.filter(user_type='admin', is_active=True)
    course_list = ', '.join(courses)
    for admin in admins:
        Notification.objects.create(
            notification_type=notif_type,
            recipient=admin,
            title='Repeat course request',
            message=(
                f'{student.registration_number} requested repeat courses '
                f'for {semester.semester_name}: {course_list}. Review required.'
            ),
            priority='high',
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_failed_courses(request):
    """All failed courses eligible for repeat request in the current academic term."""
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.select_related('program').get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    if student.status == 'graduated':
        max_ch = get_academic_policy().max_repeat_credit_hours
        return Response({'failed_courses': [], 'pending_requests': [], 'max_repeat_credit_hours': max_ch})

    current_semester = Semester.objects.filter(is_current=True).first()
    if not current_semester:
        return Response({'failed_courses': [], 'pending_requests': []})

    reconcile_repeat_registrations(student)
    pending = RepeatCourseRequest.objects.filter(
        student=student, semester=current_semester,
    ).select_related('course')
    rejected = pending.filter(status='rejected')
    pending = pending.exclude(status='rejected')

    policy = get_academic_policy()
    enrollment = Enrollment.objects.filter(student=student, semester=current_semester).first()
    enrolled_ch = _registered_credit_hours(enrollment)
    pending_repeat_ch = RepeatCourseRequest.objects.filter(
        student=student, semester=current_semester, status__in=['pending', 'approved'],
    ).aggregate(total=Sum('course__credit_hours'))['total'] or 0
    fee_paid = _semester_fee_paid(student, current_semester)
    failed_list = eligible_failed_courses_for_repeat(student, current_semester)

    return Response({
        'failed_courses': failed_list,
        'pending_requests': RepeatCourseRequestSerializer(pending, many=True).data,
        'rejected_requests': RepeatCourseRequestSerializer(rejected, many=True).data,
        'max_repeat_credit_hours': policy.max_repeat_credit_hours,
        'enrolled_credit_hours': enrolled_ch,
        'max_semester_credit_hours': policy.max_semester_credit_hours,
        'remaining_credit_hours': max(0, policy.max_semester_credit_hours - enrolled_ch - pending_repeat_ch),
        'fee_paid': fee_paid,
        'fee_error': None if fee_paid else 'Semester fee must be paid before requesting repeat courses.',
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def repeat_course_requests(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.select_related('program').get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)

    if student.status == 'graduated':
        if request.method == 'GET':
            return Response([])
        return Response({'error': 'Graduated students cannot request repeat courses.'}, status=status.HTTP_403_FORBIDDEN)

    current_semester = Semester.objects.filter(is_current=True).first()
    if not current_semester:
        return Response({'error': 'No active semester.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        qs = RepeatCourseRequest.objects.filter(student=student).select_related(
            'course', 'semester',
        ).order_by('-requested_at')
        return Response(RepeatCourseRequestSerializer(qs, many=True).data)

    if not _semester_fee_paid(student, current_semester):
        return Response(
            {'error': 'Semester fee must be paid before requesting repeat courses.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    course_ids = request.data.get('course_ids') or []
    if not course_ids:
        return Response({'error': 'course_ids is required.'}, status=status.HTTP_400_BAD_REQUEST)

    allowed_ids = failed_course_ids_for_repeat_request(student, current_semester)
    from academics.models import Course
    requested_ids = list(dict.fromkeys(course_ids))
    courses = list(Course.objects.filter(course_id__in=requested_ids))
    if len(courses) != len(requested_ids):
        found = {c.course_id for c in courses}
        missing = [cid for cid in requested_ids if cid not in found]
        return Response(
            {'error': f'Invalid course_id(s): {missing}'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    invalid = [c.course_id for c in courses if c.course_id not in allowed_ids]
    if invalid:
        return Response(
            {'error': 'One or more courses are not eligible for repeat (not failed or already requested).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing_ch = RepeatCourseRequest.objects.filter(
        student=student, semester=current_semester, status__in=['pending', 'approved'],
    ).aggregate(total=Sum('course__credit_hours'))['total'] or 0
    new_ch = sum(c.credit_hours for c in courses)
    policy = get_academic_policy()
    max_repeat_ch = policy.max_repeat_credit_hours
    if existing_ch + new_ch > max_repeat_ch:
        return Response(
            {'error': f'Repeat requests cannot exceed {max_repeat_ch} credit hours.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    summary = get_student_semester_credit_summary(student, current_semester)
    pending_new_ch = sum(
        c.credit_hours for c in courses
        if not RepeatCourseRequest.objects.filter(
            student=student, semester=current_semester, course=c,
            status__in=['pending', 'approved'],
        ).exists()
    )
    if summary['enrolled_credit_hours'] + pending_new_ch > policy.max_semester_credit_hours:
        return Response(
            {
                'error': (
                    f'Total semester load would exceed {policy.max_semester_credit_hours} CH '
                    f'(currently registered: {summary["enrolled_credit_hours"]} CH).'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    created = []
    for course in courses:
        existing = RepeatCourseRequest.objects.filter(
            student=student, semester=current_semester, course=course,
        ).first()
        if existing:
            if existing.status == 'pending':
                continue
            if existing.status == 'approved':
                continue
            if existing.status == 'rejected':
                existing.status = 'pending'
                existing.reviewed_by = None
                existing.reviewed_at = None
                existing.admin_remarks = ''
                existing.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'admin_remarks'])
                created.append(existing)
                continue
        req = RepeatCourseRequest.objects.create(
            student=student,
            semester=current_semester,
            course=course,
            status='pending',
        )
        created.append(req)

    if created:
        _notify_admins_repeat_request(
            student, [r.course.course_code for r in created], current_semester,
        )

    return Response({
        'message': f'{len(created)} repeat request(s) submitted. Pending admin approval.',
        'requests': RepeatCourseRequestSerializer(created, many=True).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('enrollments.view_enrollment')])
def list_repeat_requests(request):
    """Admin: all repeat course requests (filter ?status=pending)."""
    qs = RepeatCourseRequest.objects.select_related(
        'student__user', 'student__program', 'course', 'semester',
    ).order_by('-requested_at')
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return Response(RepeatCourseRequestSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('enrollments.view_enrollment')])
def review_repeat_request(request, request_id):
    action = request.data.get('action')
    remarks = request.data.get('remarks', '').strip()
    if action not in ('approve', 'reject'):
        return Response({'error': 'action must be approve or reject.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        repeat_req = RepeatCourseRequest.objects.select_related(
            'student', 'student__user', 'course', 'semester',
        ).get(request_id=request_id)
    except RepeatCourseRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if repeat_req.status != 'pending':
        return Response({'error': 'Request already reviewed.'}, status=status.HTTP_400_BAD_REQUEST)

    if action == 'approve':
        summary = get_student_semester_credit_summary(repeat_req.student, repeat_req.semester)
        after = summary['enrolled_credit_hours'] + repeat_req.course.credit_hours
        if after > summary['max_semester_credit_hours']:
            return Response(
                {
                    'error': (
                        f'Cannot approve — student has {summary["enrolled_credit_hours"]} CH enrolled; '
                        f'adding {repeat_req.course.credit_hours} CH would exceed the '
                        f'{summary["max_semester_credit_hours"]} CH semester limit.'
                    ),
                    'enrolled_credit_hours': summary['enrolled_credit_hours'],
                    'max_semester_credit_hours': summary['max_semester_credit_hours'],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    repeat_req.status = 'approved' if action == 'approve' else 'rejected'
    repeat_req.reviewed_by = request.user
    repeat_req.reviewed_at = timezone.now()
    repeat_req.admin_remarks = remarks
    repeat_req.save()

    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='Academic',
        defaults={'description': 'Academic updates'},
    )
    if action == 'approve':
        enroll_result = enroll_approved_repeat_request(repeat_req, request.user)
        if enroll_result.get('error'):
            repeat_req.status = 'pending'
            repeat_req.reviewed_by = None
            repeat_req.reviewed_at = None
            repeat_req.admin_remarks = ''
            repeat_req.save()
            return Response({'error': enroll_result['error']}, status=status.HTTP_400_BAD_REQUEST)
        msg = f'Your repeat request for {repeat_req.course.course_code} was approved and you are now enrolled.'
    else:
        msg = f'Your repeat request for {repeat_req.course.course_code} was rejected.'
        from enrollments.models import CourseRegistration
        CourseRegistration.objects.filter(
            student=repeat_req.student,
            course=repeat_req.course,
            status='registered',
            registration_type='repeat',
            enrollment__semester=repeat_req.semester,
        ).update(status='withdrawn')
    Notification.objects.create(
        notification_type=notif_type,
        recipient=repeat_req.student.user,
        title='Repeat course decision',
        message=msg + (f' {remarks}' if remarks else ''),
        priority='high',
    )

    return Response({
        'message': f'Repeat request {repeat_req.status}.',
        'request': RepeatCourseRequestSerializer(repeat_req).data,
    })


# ── Academic Progress ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('enrollments.view_enrollment')])
def academic_progress_semester(request):
    from .progress_utils import get_semester_progress, get_current_academic_semester

    try:
        curriculum_sem = int(request.query_params.get('curriculum_semester', 1))
    except (TypeError, ValueError):
        return Response({'error': 'curriculum_semester is required.'}, status=status.HTTP_400_BAD_REQUEST)

    academic_semester = get_current_academic_semester()
    sem_id = request.query_params.get('semester_id')
    if sem_id:
        try:
            academic_semester = Semester.objects.get(semester_id=sem_id)
        except Semester.DoesNotExist:
            return Response({'error': 'Academic semester not found.'}, status=status.HTTP_404_NOT_FOUND)

    return Response(get_semester_progress(curriculum_sem, academic_semester))


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('enrollments.view_enrollment')])
def academic_progress_repeat(request):
    from .progress_utils import get_repeat_progress, get_current_academic_semester

    academic_semester = get_current_academic_semester()
    sem_id = request.query_params.get('semester_id')
    if sem_id:
        try:
            academic_semester = Semester.objects.get(semester_id=sem_id)
        except Semester.DoesNotExist:
            return Response({'error': 'Academic semester not found.'}, status=status.HTTP_404_NOT_FOUND)

    curriculum_sem = request.query_params.get('curriculum_semester')
    if curriculum_sem is not None:
        try:
            curriculum_sem = int(curriculum_sem)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid curriculum_semester.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(get_repeat_progress(academic_semester, curriculum_sem))


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def academic_progress_promote(request):
    from .progress_utils import promote_curriculum_semester_batch, get_current_academic_semester
    from accounts.audit import log_audit

    try:
        curriculum_sem = int(request.data.get('curriculum_semester'))
    except (TypeError, ValueError):
        return Response({'error': 'curriculum_semester is required.'}, status=status.HTTP_400_BAD_REQUEST)

    academic_semester = get_current_academic_semester()
    sem_id = request.data.get('semester_id')
    if sem_id:
        try:
            academic_semester = Semester.objects.get(semester_id=sem_id)
        except Semester.DoesNotExist:
            return Response({'error': 'Academic semester not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not academic_semester:
        return Response({'error': 'No current academic semester configured.'}, status=status.HTTP_400_BAD_REQUEST)

    summary = promote_curriculum_semester_batch(curriculum_sem, academic_semester, request.user)
    if summary.get('success'):
        log_audit(
            request, 'promote_semester_batch', 'curriculum_semester',
            curriculum_sem, new_value=summary,
        )
        return Response(summary)
    return Response(summary, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_academic_status(request):
    from .progress_utils import get_student_academic_status

    if request.user.user_type != 'student':
        return Response({'error': 'Students only.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Student record not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(get_student_academic_status(student))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_academic_warnings(request):
    from accounts.access_helpers import get_faculty_profile
    from .progress_utils import get_teacher_workflow_warnings

    if request.user.user_type not in ('teacher', 'admin'):
        return Response({'error': 'Teachers only.'}, status=status.HTTP_403_FORBIDDEN)
    faculty = get_faculty_profile(request.user)
    if request.user.user_type == 'teacher' and not faculty:
        return Response({'error': 'Faculty profile required.'}, status=status.HTTP_403_FORBIDDEN)
    return Response(get_teacher_workflow_warnings(faculty))
