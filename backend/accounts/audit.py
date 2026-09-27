"""Audit log helper."""
from __future__ import annotations

from accounts.models import AuditLog


def get_client_ip(request) -> str | None:
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit(request, action_type: str, table_name: str, record_id=None, old_value=None, new_value=None):
    user = getattr(request, 'user', None)
    if user and not user.is_authenticated:
        user = None
    AuditLog.objects.create(
        user=user,
        action_type=action_type,
        table_name=table_name,
        record_id=record_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=get_client_ip(request),
    )
