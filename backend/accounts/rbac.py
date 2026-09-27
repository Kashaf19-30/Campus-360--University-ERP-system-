"""Application RBAC: Role → Permission via RolePermission."""
from __future__ import annotations

from accounts.models import Permission, Role, RolePermission, UserRole
_LEGACY_TYPE_PERMISSIONS = {
    'admin': {'*'},
    'teacher': {
        'examinations.view_examination', 'examinations.create_examination',
        'examinations.enter_marks', 'examinations.request_marks_edit',
        'examinations.view_marks', 'attendance.mark_attendance',
        'attendance.view_attendance', 'announcements.create_announcement',
        'announcements.view_announcement', 'complaints.view_complaint',
        'complaints.create_complaint', 'faculty.view_own_profile',
        'students.view_student', 'academics.view_offering',
    },
    'student': {
        'examinations.view_own_results', 'examinations.view_own_grades',
        'enrollments.view_own_enrollment',
        'complaints.create_complaint', 'complaints.view_own_complaint',
        'announcements.view_announcement', 'students.view_own_profile',
        'fees.view_own_fees', 'attendance.view_own_attendance',
    },
    'applicant': {'admissions.submit_application', 'admissions.view_own_application'},
    'finance_officer': {
        'fees.view_fees', 'fees.manage_fees', 'admissions.view_application',
    },
}


def get_user_role_names(user) -> list[str]:
    return list(
        UserRole.objects.filter(user=user).select_related('role').values_list('role__role_name', flat=True)
    )


def get_user_permission_names(user) -> set[str]:
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser or user.user_type == 'admin':
        return {'*'}
    role_names = get_user_role_names(user)
    if 'Admin' in role_names:
        return {'*'}
    role_ids = list(UserRole.objects.filter(user=user).values_list('role_id', flat=True))
    legacy = _LEGACY_TYPE_PERMISSIONS.get(user.user_type, set())
    if not role_ids:
        if '*' in legacy:
            return {'*'}
        return set(legacy)
    return set(
        RolePermission.objects.filter(role_id__in=role_ids)
        .values_list('permission__permission_name', flat=True)
    )


def user_has_permission(user, permission_name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    perms = get_user_permission_names(user)
    if '*' in perms:
        return True
    return permission_name in perms


def ensure_user_role_for_type(user, assigned_by=None):
    """Assign default Role row from user_type if missing."""
    type_to_role = {
        'admin': 'Admin',
        'teacher': 'Teacher',
        'student': 'Student',
        'applicant': 'Applicant',
        'finance_officer': 'Finance Officer',
    }
    role_name = type_to_role.get(user.user_type)
    if not role_name:
        return
    role = Role.objects.filter(role_name=role_name).first()
    if not role:
        return
    UserRole.objects.get_or_create(
        user=user,
        role=role,
        defaults={'assigned_by': assigned_by},
    )
