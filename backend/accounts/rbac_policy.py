"""
Rules for which roles and permissions admins may assign via the UI/API.
"""
from accounts.management.commands.seed_rbac import APPLICANT_PERMS, STUDENT_PERMS, TEACHER_PERMS

EDITABLE_ROLE_NAMES = frozenset({'Teacher', 'Student', 'Applicant'})
PROTECTED_ROLE_NAME = 'Admin'

BLOCKED_FOR_NON_ADMIN = frozenset({
    'system.admin_access',
    'system.view_audit_log',
    'system.manage_role_permissions',
    'accounts.create_credentials',
})

# Minimum permissions each role must retain (matches seed defaults)
MINIMUM_ROLE_PERMISSIONS = {
    'Teacher': frozenset(TEACHER_PERMS),
    'Student': frozenset(STUDENT_PERMS),
    'Applicant': frozenset(APPLICANT_PERMS),
}


def validate_role_permission_update(role, permission_names: list[str]) -> tuple[bool, str | None]:
    if role.role_name == PROTECTED_ROLE_NAME:
        return False, 'Admin role permissions are fixed and cannot be modified.'
    if role.role_name not in EDITABLE_ROLE_NAMES:
        return False, f'Role "{role.role_name}" is not editable.'
    blocked = [p for p in permission_names if p in BLOCKED_FOR_NON_ADMIN]
    if blocked:
        return False, f'Cannot assign privileged permissions: {", ".join(blocked)}'
    minimum = MINIMUM_ROLE_PERMISSIONS.get(role.role_name, frozenset())
    granted = set(permission_names)
    missing = minimum - granted
    if missing:
        return False, f'Cannot remove required permissions: {", ".join(sorted(missing))}'
    return True, None
