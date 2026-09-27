from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from accounts.permissions import IsAdmin, require_permission
from students.models import Student
from academics.models import DegreeProgram, Semester, CourseOffering
from .models import NotificationType, Notification, Announcement
from .serializers import NotificationTypeSerializer, NotificationSerializer, AnnouncementSerializer


def _teacher_eligible_offerings(faculty):
    """Active enrolled courses where marks are not yet submitted (not completed)."""
    return CourseOffering.objects.filter(
        faculty=faculty,
        is_active=True,
        marks_locked=False,
    ).select_related('course', 'semester')


def _teacher_owns_eligible_offering(faculty, offering_id):
    try:
        offering_id = int(offering_id)
    except (TypeError, ValueError):
        return None
    return _teacher_eligible_offerings(faculty).filter(offering_id=offering_id).first()


def _parse_target_audience_option(data):
    """Map target_audience_option to model fields. Returns data dict."""
    target_opt = data.get('target_audience_option') or data.get('target_audience')
    if not target_opt:
        return data
    if target_opt.startswith('offering_'):
        offering_id = target_opt.split('_', 1)[1]
        data['target_audience'] = 'course_offering'
        data['target_offering'] = offering_id
        data['target_program'] = None
        data['target_semester'] = None
    elif target_opt.startswith('batch_'):
        data['target_audience'] = target_opt
        data['target_program'] = None
        data['target_semester'] = None
        data['target_offering'] = None
    elif target_opt.startswith('program_'):
        prog_id = target_opt.split('_', 1)[1]
        data['target_audience'] = 'specific_program'
        data['target_program'] = prog_id
        data['target_semester'] = None
        data['target_offering'] = None
    elif target_opt.startswith('semester_'):
        sem_id = target_opt.split('_', 1)[1]
        data['target_audience'] = 'students'
        data['target_program'] = None
        data['target_semester'] = sem_id
        data['target_offering'] = None
    else:
        data['target_audience'] = target_opt
    return data


def _recipients_for_announcement(announcement):
    """Resolve active users who should receive an in-app notification."""
    from accounts.models import User

    audience = announcement.target_audience or 'all'
    qs = User.objects.filter(is_active=True)

    if audience == 'course_offering' and announcement.target_offering_id:
        from enrollments.models import CourseRegistration
        student_ids = CourseRegistration.objects.filter(
            offering_id=announcement.target_offering_id,
            status='registered',
        ).values_list('student_id', flat=True)
        return qs.filter(user_type='student', student_profile__student_id__in=student_ids)
    if audience == 'students':
        if announcement.target_semester_id:
            from enrollments.models import Enrollment
            enrolled_student_ids = Enrollment.objects.filter(
                semester_id=announcement.target_semester_id,
            ).values_list('student_id', flat=True)
            return qs.filter(user_type='student', student_profile__student_id__in=enrolled_student_ids)
        return qs.filter(user_type='student')
    if audience in ('faculty', 'teachers'):
        return qs.filter(user_type='teacher')
    if audience == 'staff':
        return qs.exclude(user_type__in=['student', 'teacher', 'applicant'])
    if audience == 'specific_program' and announcement.target_program_id:
        return qs.filter(user_type='student', student_profile__program_id=announcement.target_program_id)
    if audience.startswith('batch_'):
        try:
            batch_year = int(audience.split('_', 1)[1])
            return qs.filter(user_type='student', student_profile__batch_year=batch_year)
        except (IndexError, ValueError):
            return qs.none()
    if audience.startswith('semester_') and announcement.target_semester_id:
        from enrollments.models import Enrollment
        enrolled_student_ids = Enrollment.objects.filter(
            semester_id=announcement.target_semester_id,
        ).values_list('student_id', flat=True)
        return qs.filter(user_type='student', student_profile__student_id__in=enrolled_student_ids)
    return qs


def _fan_out_announcement_notifications(announcement):
    """Create inbox Notification rows so announcements appear under My Notifications."""
    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='General',
        defaults={'description': 'General campus notifications'},
    )
    recipients = _recipients_for_announcement(announcement).distinct()
    Notification.objects.bulk_create([
        Notification(
            notification_type=notif_type,
            recipient=user,
            title=announcement.title,
            message=announcement.content,
            priority=announcement.priority,
        )
        for user in recipients.iterator(chunk_size=500)
    ], batch_size=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_my_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user)
    unread_only = request.query_params.get('unread')
    if unread_only == 'true':
        notifications = notifications.filter(is_read=False)
    return Response(NotificationSerializer(notifications, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_read(request, notification_id):
    try:
        notification = Notification.objects.get(notification_id=notification_id, recipient=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=['is_read', 'read_at'])
    return Response({'message': 'Marked as read.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return Response({'message': 'All notifications marked as read.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_announcements(request):
    now = timezone.now()
    qs = Announcement.objects.filter(is_active=True)
    qs = qs.filter(Q(expires_date__isnull=True) | Q(expires_date__gte=now))

    user_type = request.user.user_type
    if user_type == 'student':
        student = Student.objects.filter(user=request.user).first()
        if student:
            from enrollments.models import Enrollment, CourseRegistration
            enrolled_semester_ids = list(
                Enrollment.objects.filter(student=student).values_list('semester_id', flat=True)
            )
            enrolled_offering_ids = list(
                CourseRegistration.objects.filter(
                    student=student, status='registered',
                ).values_list('offering_id', flat=True)
            )
            qs = qs.filter(
                Q(target_audience='all') |
                Q(target_audience='students', target_semester__isnull=True) |
                Q(target_audience='students', target_semester_id__in=enrolled_semester_ids) |
                Q(target_audience=f'batch_{student.batch_year}') |
                Q(target_audience='specific_program', target_program=student.program) |
                Q(target_audience='course_offering', target_offering_id__in=enrolled_offering_ids)
            )
        else:
            qs = qs.filter(target_audience__in=['all', 'students'], target_semester__isnull=True)
    elif user_type == 'teacher':
        qs = qs.filter(
            Q(target_audience='all') |
            Q(target_audience='faculty') |
            Q(target_audience='teachers') |
            Q(created_by=request.user)
        )
    # Admin sees all; filter own for admin dashboard optional
    if user_type == 'admin' and request.query_params.get('mine') == '1':
        qs = qs.filter(created_by=request.user)

    return Response(AnnouncementSerializer(qs.order_by('-created_at'), many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('announcements.create_announcement')])
def create_announcement(request):
    if request.user.user_type not in ['admin', 'teacher']:
        return Response({'error': 'Permission denied. Only Admins and Teachers can create announcements.'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data.copy()

    if request.user.user_type == 'teacher':
        allowed_types = {'academic', 'general'}
        ann_type = data.get('announcement_type', 'general')
        if ann_type not in allowed_types:
            return Response(
                {'error': 'Teachers can only create academic or general announcements.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        from faculty.models import Faculty
        try:
            faculty = Faculty.objects.get(user=request.user)
        except Faculty.DoesNotExist:
            return Response({'error': 'Faculty profile required.'}, status=status.HTTP_403_FORBIDDEN)

        target_opt = data.get('target_audience_option') or data.get('target_audience') or ''
        if not str(target_opt).startswith('offering_'):
            return Response(
                {'error': 'Select one of your active enrolled courses as the announcement audience.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        offering_id = target_opt.split('_', 1)[1]
        offering = _teacher_owns_eligible_offering(faculty, offering_id)
        if not offering:
            return Response(
                {'error': 'You can only announce to your active courses that are not yet completed.'},
                status=status.HTTP_403_FORBIDDEN,
            )
    
    # Map context to content if sent
    if 'context' in data and 'content' not in data:
        data['content'] = data['context']

    data = _parse_target_audience_option(data)

    serializer = AnnouncementSerializer(data=data)
    if serializer.is_valid():
        announcement = serializer.save(created_by=request.user)
        _fan_out_announcement_notifications(announcement)
        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def announcement_detail(request, announcement_id):
    try:
        announcement = Announcement.objects.get(announcement_id=announcement_id)
    except Announcement.DoesNotExist:
        return Response({'error': 'Announcement not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Permission check for write operations
    if request.method in ['PUT', 'DELETE']:
        if request.user.user_type != 'admin' and announcement.created_by != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(AnnouncementSerializer(announcement).data)

    if request.method == 'PUT':
        data = request.data.copy()
        
        # Map context to content if sent
        if 'context' in data and 'content' not in data:
            data['content'] = data['context']

        if request.user.user_type == 'teacher':
            from faculty.models import Faculty
            target_opt = data.get('target_audience_option') or data.get('target_audience') or ''
            if target_opt.startswith('offering_'):
                faculty = Faculty.objects.filter(user=request.user).first()
                offering = _teacher_owns_eligible_offering(faculty, target_opt.split('_', 1)[1]) if faculty else None
                if not offering:
                    return Response(
                        {'error': 'You can only announce to your active courses that are not yet completed.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        data = _parse_target_audience_option(data)

        serializer = AnnouncementSerializer(announcement, data=data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            if data.get('title') or data.get('content') or data.get('context'):
                _fan_out_announcement_notifications(updated)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE method: mark inactive or delete
    announcement.is_active = False
    announcement.save(update_fields=['is_active'])
    return Response({'message': 'Announcement deactivated.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_announcement_target_options(request):
    """Retrieve dynamic targeting options for announcements."""
    if request.user.user_type == 'teacher':
        from faculty.models import Faculty
        try:
            faculty = Faculty.objects.get(user=request.user)
        except Faculty.DoesNotExist:
            return Response([])
        options = []
        for offering in _teacher_eligible_offerings(faculty).order_by('course__course_code'):
            options.append({
                'value': f'offering_{offering.offering_id}',
                'label': f'{offering.course.course_code} — {offering.course.course_name} (enrolled students)',
                'offering_id': offering.offering_id,
            })
        return Response(options)

    batches = Student.objects.filter(status='active').values_list('batch_year', flat=True).distinct()
    
    options = [
        {'value': 'all', 'label': 'All'},
        {'value': 'students', 'label': 'All Students'},
        {'value': 'faculty', 'label': 'Teachers'},
    ]
    
    for b in sorted(batches):
        options.append({
            'value': f'batch_{b}',
            'label': f'Batch {b} Students'
        })
        
    # 2. Add Programs
    programs = DegreeProgram.objects.filter(is_active=True)
    for p in programs:
        options.append({
            'value': f'program_{p.program_id}',
            'label': f'{p.program_name} Students'
        })
        
    # 3. Add Semesters
    semesters = Semester.objects.all()
    for s in semesters:
        options.append({
            'value': f'semester_{s.semester_id}',
            'label': f'Semester: {s.semester_name}'
        })
        
    return Response(options)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notification_types(request):
    return Response(NotificationTypeSerializer(NotificationType.objects.all(), many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_notification_type(request):
    serializer = NotificationTypeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)