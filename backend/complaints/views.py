from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from accounts.permissions import require_permission, require_any_permission
from accounts.access_helpers import can_view_complaint, can_use_complaint_thread
from accounts.rbac import user_has_permission
from notifications.system_notify import notify_user
from .models import ComplaintCategory, Complaint, ComplaintLog, CommunicationThread, Message, Feedback
from .serializers import (
    ComplaintCategorySerializer, ComplaintSerializer, ComplaintLogSerializer,
    CommunicationThreadSerializer, MessageSerializer, FeedbackSerializer,
)

CLOSED_STATUSES = ('resolved', 'rejected', 'closed')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_categories(request):
    return Response(ComplaintCategorySerializer(ComplaintCategory.objects.all(), many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('complaints.manage_complaint')])
def create_category(request):
    serializer = ComplaintCategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_complaint(request):
    if not user_has_permission(request.user, 'complaints.create_complaint'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    serializer = ComplaintSerializer(data=request.data)
    if serializer.is_valid():
        complaint = serializer.save(submitted_by=request.user)
        ComplaintLog.objects.create(
            complaint=complaint,
            action_type='submitted',
            performed_by=request.user,
            new_status='pending',
        )
        thread, _ = CommunicationThread.objects.get_or_create(
            complaint=complaint,
            defaults={'subject': complaint.subject, 'created_by': request.user},
        )
        Message.objects.create(
            thread=thread,
            sender=request.user,
            message_text=complaint.description,
        )
        notify_user(
            request.user,
            'Complaints',
            'Complaint submitted',
            f'Your complaint "{complaint.subject}" was received and is pending review.',
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_complaints(request):
    if not user_has_permission(request.user, 'complaints.view_own_complaint'):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
    complaints = Complaint.objects.select_related('category').filter(submitted_by=request.user)
    return Response(ComplaintSerializer(complaints, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission('complaints.view_complaint', 'complaints.manage_complaint')])
def list_all_complaints(request):
    qs = Complaint.objects.select_related('category', 'submitted_by').all()
    status_filter = request.query_params.get('status')
    active_only = request.query_params.get('active') == 'true'
    if active_only:
        qs = qs.exclude(status__in=CLOSED_STATUSES)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return Response(ComplaintSerializer(qs, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('complaints.manage_complaint')])
def admin_update_complaint_status(request, complaint_id):
    try:
        complaint = Complaint.objects.select_related('submitted_by').get(complaint_id=complaint_id)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    admin_response = request.data.get('admin_response', '').strip()

    if complaint.status in CLOSED_STATUSES:
        return Response({'error': 'This complaint is closed and cannot be modified.'}, status=status.HTTP_400_BAD_REQUEST)

    if new_status not in ('in_progress', 'resolved', 'rejected'):
        return Response({'error': 'Status must be in_progress, resolved, or rejected.'}, status=status.HTTP_400_BAD_REQUEST)

    if new_status in ('resolved', 'rejected') and not admin_response:
        return Response({'error': 'A response message is required when resolving or rejecting.'}, status=status.HTTP_400_BAD_REQUEST)

    old_status = complaint.status
    complaint.status = new_status
    if new_status in ('resolved', 'rejected'):
        complaint.admin_response = admin_response
        complaint.resolved_at = timezone.now()
        complaint.save(update_fields=['status', 'admin_response', 'resolved_at'])
        thread, _ = CommunicationThread.objects.get_or_create(
            complaint=complaint,
            defaults={'subject': complaint.subject, 'created_by': request.user},
        )
        Message.objects.create(
            thread=thread,
            sender=request.user,
            message_text=admin_response,
        )
    else:
        complaint.save(update_fields=['status'])

    ComplaintLog.objects.create(
        complaint=complaint,
        action_type='updated',
        performed_by=request.user,
        previous_status=old_status,
        new_status=new_status,
        remarks=admin_response or 'Status updated to under review.',
    )
    notify_user(
        complaint.submitted_by,
        'Complaints',
        f'Complaint {new_status.replace("_", " ")}',
        f'Your complaint "{complaint.subject}" is now {new_status.replace("_", " ")}.',
    )
    return Response(ComplaintSerializer(complaint, context={'request': request}).data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def complaint_detail(request, complaint_id):
    try:
        complaint = Complaint.objects.select_related('category').get(complaint_id=complaint_id)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not can_view_complaint(request.user, complaint):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(ComplaintSerializer(complaint, context={'request': request}).data)

    if request.method == 'DELETE':
        if complaint.submitted_by != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        if complaint.status in CLOSED_STATUSES:
            return Response({'error': 'Closed complaints cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        complaint.delete()
        return Response({'message': 'Complaint deleted successfully.'})

    if complaint.status in CLOSED_STATUSES:
        return Response({'error': 'Closed complaints cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

    if complaint.submitted_by != request.user and not user_has_permission(
        request.user, 'complaints.manage_complaint'
    ):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    allowed_fields = {'description', 'subject', 'category'}
    data = {k: v for k, v in request.data.items() if k in allowed_fields}
    if not data:
        return Response({'error': 'No editable fields provided.'}, status=status.HTTP_400_BAD_REQUEST)

    old_status = complaint.status
    serializer = ComplaintSerializer(complaint, data=data, partial=True)
    if serializer.is_valid():
        updated = serializer.save()
        if updated.status != old_status:
            ComplaintLog.objects.create(
                complaint=updated,
                action_type='updated',
                performed_by=request.user,
                previous_status=old_status,
                new_status=updated.status,
            )
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def complaint_thread(request, complaint_id):
    try:
        complaint = Complaint.objects.get(complaint_id=complaint_id)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not can_use_complaint_thread(request.user, complaint):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            thread = CommunicationThread.objects.prefetch_related('messages__sender').get(complaint=complaint)
        except CommunicationThread.DoesNotExist:
            thread = CommunicationThread.objects.create(
                complaint=complaint, subject=complaint.subject, created_by=complaint.submitted_by,
            )
        return Response(CommunicationThreadSerializer(thread).data)

    if complaint.status in CLOSED_STATUSES:
        return Response({'error': 'Cannot post messages on a closed complaint.'}, status=status.HTTP_400_BAD_REQUEST)

    if not can_use_complaint_thread(request.user, complaint):
        return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    message_text = (request.data.get('message_text') or '').strip()
    if len(message_text) < 2:
        return Response({'error': 'Message text is required (min 2 characters).'}, status=status.HTTP_400_BAD_REQUEST)

    thread, _ = CommunicationThread.objects.get_or_create(
        complaint=complaint,
        defaults={'subject': complaint.subject, 'created_by': request.user},
    )
    message = Message.objects.create(
        thread=thread,
        sender=request.user,
        message_text=message_text,
    )
    other = complaint.submitted_by
    if request.user == complaint.submitted_by:
        from accounts.models import User
        for admin in User.objects.filter(user_type='admin', is_active=True):
            notify_user(admin, 'Complaints', 'New complaint message', message_text[:200])
    else:
        notify_user(other, 'Complaints', 'Reply on your complaint', message_text[:200])
    return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request, complaint_id):
    try:
        complaint = Complaint.objects.get(complaint_id=complaint_id)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)

    if complaint.submitted_by != request.user:
        return Response({'error': 'You can only give feedback on your own complaints.'}, status=status.HTTP_403_FORBIDDEN)

    if complaint.status not in CLOSED_STATUSES:
        return Response({'error': 'Feedback can only be submitted for resolved or rejected complaints.'}, status=status.HTTP_400_BAD_REQUEST)

    if Feedback.objects.filter(complaint=complaint, user=request.user).exists():
        return Response({'error': 'You have already submitted feedback for this complaint.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = FeedbackSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(complaint=complaint, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_any_permission('complaints.view_complaint', 'complaints.manage_complaint')])
def list_feedback(request, complaint_id):
    try:
        complaint = Complaint.objects.get(complaint_id=complaint_id)
    except Complaint.DoesNotExist:
        return Response({'error': 'Complaint not found.'}, status=status.HTTP_404_NOT_FOUND)

    feedback = Feedback.objects.filter(complaint=complaint)
    return Response(FeedbackSerializer(feedback, many=True).data)
