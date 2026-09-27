"""System-generated in-app notifications (not user-composed)."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from .models import Notification, NotificationType

User = get_user_model()

# Standard notification type names used across the ERP
NOTIFICATION_TYPES = {
    'Registration': 'Course registration and enrollment',
    'Admissions': 'Admission pipeline updates',
    'Finance': 'Fee and challan updates',
    'Academic': 'Academic progress and standing',
    'Attendance': 'Attendance warnings',
    'Examination': 'Marks and examination updates',
    'Complaints': 'Complaint status updates',
    'General': 'Campus announcements (system fan-out)',
}


def ensure_notification_types() -> None:
    for type_name, description in NOTIFICATION_TYPES.items():
        NotificationType.objects.get_or_create(
            type_name=type_name,
            defaults={'description': description},
        )


def notify_user(user, type_name: str, title: str, message: str, priority: str = 'normal'):
    if not user or not getattr(user, 'is_active', True):
        return None
    notif_type, _ = NotificationType.objects.get_or_create(
        type_name=type_name,
        defaults={'description': NOTIFICATION_TYPES.get(type_name, type_name)},
    )
    return Notification.objects.create(
        notification_type=notif_type,
        recipient=user,
        title=title,
        message=message,
        priority=priority,
    )


def notify_users(users, type_name: str, title: str, message: str, priority: str = 'normal'):
    ensure_notification_types()
    created = []
    for user in users:
        n = notify_user(user, type_name, title, message, priority)
        if n:
            created.append(n)
    return created


def notify_admins(type_name: str, title: str, message: str, priority: str = 'high'):
    admins = User.objects.filter(user_type='admin', is_active=True)
    return notify_users(admins, type_name, title, message, priority)
