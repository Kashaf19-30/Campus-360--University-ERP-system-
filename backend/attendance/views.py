from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Max
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import require_permission, require_any_permission
from students.models import Student
from academics.models import CourseOffering
from academics.display_utils import offering_teacher_name
from enrollments.models import CourseRegistration
from .models import Attendance, AttendanceRecord, StudentAttendanceSummary, LeaveApplication
from .serializers import AttendanceSerializer, AttendanceRecordSerializer, StudentAttendanceSummarySerializer, LeaveApplicationSerializer
from academics.policy_utils import get_academic_policy


from accounts.access_helpers import get_faculty_profile, teacher_owns_offering, user_is_admin


def _apply_attendance_filters(qs, request, offering_prefix='offering'):
    """Filter attendance queries by department, program, semester, and course."""
    from academics.models import DegreeProgram, ProgramCourse

    semester = request.query_params.get('semester')
    course = request.query_params.get('course')
    program = request.query_params.get('program')
    department = request.query_params.get('department')

    if semester:
        qs = qs.filter(**{f'{offering_prefix}__semester_id': semester})
    if course:
        qs = qs.filter(**{f'{offering_prefix}__course_id': course})
    if program:
        course_ids = ProgramCourse.objects.filter(program_id=program).values_list('course_id', flat=True)
        qs = qs.filter(**{f'{offering_prefix}__course_id__in': course_ids})
    elif department:
        program_ids = DegreeProgram.objects.filter(department_id=department).values_list('program_id', flat=True)
        course_ids = ProgramCourse.objects.filter(program_id__in=program_ids).values_list('course_id', flat=True)
        qs = qs.filter(**{f'{offering_prefix}__course_id__in': course_ids})
    return qs


def _student_has_approved_leave(student_id, offering_id, attendance_date):
    """True when an approved leave covers this student, course offering, and date."""
    if not student_id or not offering_id or not attendance_date:
        return False
    return LeaveApplication.objects.filter(
        student_id=student_id,
        offering_id=offering_id,
        status='approved',
        start_date__lte=attendance_date,
        end_date__gte=attendance_date,
    ).exists()


def _next_lecture_number(offering_id):
    last = Attendance.objects.filter(offering_id=offering_id).aggregate(
        max_lec=Max('lecture_number')
    )['max_lec']
    return (last or 0) + 1


def _update_summary(record):
    summary, _ = StudentAttendanceSummary.objects.get_or_create(
        student=record.student,
        offering=record.attendance.offering,
        course=record.attendance.offering.course,
        semester=record.attendance.offering.semester,
    )
    offering = record.attendance.offering
    was_below = summary.is_below_threshold
    conducted_lectures = Attendance.objects.filter(offering=offering).count()
    summary.total_lectures = max(conducted_lectures, 1)

    summary.attended_lectures = AttendanceRecord.objects.filter(
        student=record.student,
        attendance__offering=offering,
        status='present'
    ).count()

    summary.leave_count = AttendanceRecord.objects.filter(
        student=record.student,
        attendance__offering=offering,
        status='leave'
    ).count()

    if conducted_lectures > 0:
        summary.attendance_percentage = (summary.attended_lectures / conducted_lectures) * 100.0
    else:
        summary.attendance_percentage = 100.0

    min_pct = float(get_academic_policy().min_attendance_percentage)
    summary.is_below_threshold = summary.attendance_percentage < min_pct
    summary.save()

    if summary.is_below_threshold and not was_below:
        from notifications.system_notify import notify_user
        course_code = offering.course.course_code
        pct = f'{summary.attendance_percentage:.1f}'
        notify_user(
            record.student.user,
            'Attendance',
            f'Low attendance — {course_code}',
            f'Your attendance in {course_code} is {pct}% (below {min_pct:g}% required).',
            priority='high',
        )
        if offering.faculty_id and offering.faculty.user_id:
            notify_user(
                offering.faculty.user,
                'Attendance',
                f'Student below {min_pct:g}% — {course_code}',
                (
                    f'{record.student.registration_number} has {pct}% attendance '
                    f'in {course_code}. Review required.'
                ),
                priority='normal',
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('attendance.mark_attendance')])
def mark_attendance(request):
    faculty = get_faculty_profile(request.user)
    if not faculty:
        return Response({'error': 'Only faculty can mark attendance.'}, status=status.HTTP_403_FORBIDDEN)

    offering_id = request.data.get('offering_id')
    attendance_date = request.data.get('attendance_date')
    lecture_number = request.data.get('lecture_number')
    topic_covered = request.data.get('topic_covered', '')
    records_data = request.data.get('records', [])

    if not offering_id:
        course_id = request.data.get('course_id') or request.data.get('course')
        if course_id:
            off_obj = CourseOffering.objects.filter(course_id=course_id, is_active=True).first()
            if off_obj:
                offering_id = off_obj.offering_id

    if not offering_id or not attendance_date:
        return Response({'error': 'offering_id and attendance_date are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        offering = CourseOffering.objects.get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.user_type == 'teacher' and not teacher_owns_offering(request.user, offering):
        return Response({'error': 'You can only mark attendance for your own offerings.'}, status=status.HTTP_403_FORBIDDEN)

    from examinations.marks_locking import offering_bulk_unlock_active
    if offering.marks_locked and not offering_bulk_unlock_active(offering):
        return Response(
            {'error': 'Final marks submitted — attendance is closed for this course.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not lecture_number:
        lecture_number = _next_lecture_number(offering_id)

    attendance, created = Attendance.objects.get_or_create(
        offering_id=offering_id,
        attendance_date=attendance_date,
        lecture_number=lecture_number,
        defaults={'marked_by': faculty, 'topic_covered': topic_covered}
    )

    if not created:
        return Response({'error': 'Attendance already marked for this session.'}, status=status.HTTP_400_BAD_REQUEST)

    created_records = []
    for entry in records_data:
        student_id = entry.get('student')
        if _student_has_approved_leave(student_id, offering_id, attendance_date):
            entry['status'] = 'leave'
            if not (entry.get('remarks') or '').strip():
                entry['remarks'] = 'Approved leave'
        reg = CourseRegistration.objects.filter(
            student_id=student_id, offering_id=offering_id, status='registered'
        ).first()
        if reg:
            entry['registration'] = reg.registration_id
        entry['attendance'] = attendance.attendance_id
        serializer = AttendanceRecordSerializer(data=entry)
        if serializer.is_valid():
            record = serializer.save()
            created_records.append(serializer.data)
            _update_summary(record)

    return Response({
        'attendance': AttendanceSerializer(attendance).data,
        'records': created_records,
        'lecture_number': lecture_number,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission('attendance.view_attendance', 'attendance.mark_attendance')])
def list_attendance(request):
    offering = request.query_params.get('offering')
    qs = Attendance.objects.select_related('offering__course', 'offering__semester').all()
    if request.user.user_type == 'teacher':
        faculty = get_faculty_profile(request.user)
        if faculty:
            qs = qs.filter(
                offering__faculty=faculty,
                offering__is_active=True,
                offering__marks_locked=False,
            )
        else:
            qs = qs.none()
    if offering:
        qs = qs.filter(offering__offering_id=offering)
    qs = _apply_attendance_filters(qs, request)
    return Response(AttendanceSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission('attendance.mark_attendance', 'attendance.view_attendance')])
def next_lecture_number(request):
    offering_id = request.query_params.get('offering_id')
    if not offering_id:
        return Response({'error': 'offering_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        offering = CourseOffering.objects.select_related('faculty').get(offering_id=offering_id)
    except CourseOffering.DoesNotExist:
        return Response({'error': 'Course offering not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.user_type == 'teacher':
        if not teacher_owns_offering(request.user, offering):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    elif not user_is_admin(request.user):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    return Response({'lecture_number': _next_lecture_number(offering_id)})


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('attendance.view_own_attendance')])
def my_attendance_summary(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'No student record found.'}, status=status.HTTP_404_NOT_FOUND)
    summaries = StudentAttendanceSummary.objects.select_related('course', 'semester').filter(student=student)
    offering_id = request.query_params.get('offering')
    course_id = request.query_params.get('course_id')
    if offering_id:
        summaries = summaries.filter(offering_id=offering_id)
    elif course_id:
        summaries = summaries.filter(course_id=course_id)
    return Response(StudentAttendanceSummarySerializer(summaries, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('attendance.view_attendance')])
def list_attendance_summaries(request):
    offering = request.query_params.get('offering')
    qs = StudentAttendanceSummary.objects.select_related(
        'student', 'student__program', 'course', 'semester', 'offering',
    ).all()
    if request.user.user_type == 'teacher':
        faculty = get_faculty_profile(request.user)
        if faculty:
            qs = qs.filter(
                offering__faculty=faculty,
                offering__is_active=True,
                offering__marks_locked=False,
            )
        else:
            qs = qs.none()
    if offering:
        qs = qs.filter(offering__offering_id=offering)
    program = request.query_params.get('program')
    department = request.query_params.get('department')
    if program:
        qs = qs.filter(student__program_id=program)
    elif department:
        qs = qs.filter(student__program__department_id=department)
    qs = _apply_attendance_filters(qs, request)
    return Response(StudentAttendanceSummarySerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('attendance.view_attendance')])
def export_attendance_report(request):
    """CSV export of attendance summaries for HOD/dean reporting."""
    import csv
    from django.http import HttpResponse

    offering = request.query_params.get('offering')
    qs = StudentAttendanceSummary.objects.select_related(
        'student', 'course', 'semester', 'offering',
    ).all()
    if request.user.user_type == 'teacher':
        faculty = get_faculty_profile(request.user)
        if faculty:
            qs = qs.filter(offering__faculty=faculty)
        else:
            qs = qs.none()
    if offering:
        qs = qs.filter(offering__offering_id=offering)
    program = request.query_params.get('program')
    department = request.query_params.get('department')
    if program:
        qs = qs.filter(student__program_id=program)
    elif department:
        qs = qs.filter(student__program__department_id=department)
    qs = _apply_attendance_filters(qs, request)

    min_pct = float(get_academic_policy().min_attendance_percentage)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Registration No', 'Course', 'Teacher', 'Semester',
        'Total Lectures', 'Attended', 'Leave', 'Percentage', f'Below {min_pct:g}%',
    ])
    for s in qs:
        writer.writerow([
            s.student.registration_number,
            s.course.course_code,
            offering_teacher_name(s.offering, default='—') if s.offering_id else '—',
            s.semester.semester_name,
            s.total_lectures,
            s.attended_lectures,
            s.leave_count,
            f'{s.attendance_percentage:.1f}',
            'Yes' if s.is_below_threshold else 'No',
        ])
    return response


# ── Leave Applications ────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_leave(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can submit leave applications.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Student record not found.'}, status=status.HTTP_404_NOT_FOUND)

    data = {**request.data, 'student': student.student_id}
    if 'section' in data and 'offering' not in data:
        data['offering'] = data.pop('section')
    if not data.get('offering'):
        return Response({'error': 'Course selection is required.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = LeaveApplicationSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_leaves(request):
    if request.user.user_type != 'student':
        return Response({'error': 'Only students can access this.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Student record not found.'}, status=status.HTTP_404_NOT_FOUND)
    leaves = LeaveApplication.objects.select_related('offering__course').filter(student=student)
    return Response(LeaveApplicationSerializer(leaves, many=True).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_leave(request, leave_id):
    try:
        leave = LeaveApplication.objects.get(leave_id=leave_id)
    except LeaveApplication.DoesNotExist:
        return Response({'error': 'Leave application not found.'}, status=status.HTTP_404_NOT_FOUND)
    if leave.student.user != request.user:
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    if leave.status == 'approved':
        return Response({'error': 'Approved leave applications cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
    if leave.status not in ('pending', 'rejected'):
        return Response({'error': 'This leave application cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
    leave.delete()
    return Response({'message': 'Leave application deleted.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('attendance.mark_attendance')])
def teacher_leaves(request):
    faculty = get_faculty_profile(request.user)
    if not faculty and request.user.user_type != 'admin':
        return Response({'error': 'Faculty profile required.'}, status=status.HTTP_403_FORBIDDEN)
    qs = LeaveApplication.objects.select_related('student__user', 'offering__course', 'offering__faculty__user').filter(status='pending')
    if request.user.user_type == 'teacher' and faculty:
        qs = qs.filter(offering__faculty=faculty)
    return Response(LeaveApplicationSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('attendance.mark_attendance')])
def review_leave(request, leave_id):
    try:
        leave = LeaveApplication.objects.select_related('offering', 'student').get(leave_id=leave_id)
    except LeaveApplication.DoesNotExist:
        return Response({'error': 'Leave application not found.'}, status=status.HTTP_404_NOT_FOUND)

    faculty = get_faculty_profile(request.user)
    if request.user.user_type == 'teacher':
        if not leave.offering_id:
            return Response({'error': 'Leave application has no course assigned.'}, status=status.HTTP_400_BAD_REQUEST)
        if not faculty or leave.offering.faculty_id != faculty.faculty_id:
            return Response({'error': 'You can only review leaves for your offerings.'}, status=status.HTTP_403_FORBIDDEN)

    action = request.data.get('action')
    remarks = request.data.get('teacher_remarks', '').strip()
    if action not in ('approved', 'rejected'):
        return Response({'error': 'action must be approved or rejected.'}, status=status.HTTP_400_BAD_REQUEST)
    if action == 'rejected' and not remarks:
        return Response({'error': 'Remarks required when rejecting leave.'}, status=status.HTTP_400_BAD_REQUEST)
    if action == 'approved' and not leave.offering_id:
        return Response({'error': 'Leave application has no course assigned.'}, status=status.HTTP_400_BAD_REQUEST)

    leave.status = action
    leave.teacher_remarks = remarks
    leave.reviewed_by = request.user
    leave.reviewed_at = timezone.now()
    leave.save()

    return Response(LeaveApplicationSerializer(leave).data)
