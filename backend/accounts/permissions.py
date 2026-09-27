from rest_framework.permissions import BasePermission, IsAuthenticated

from accounts.rbac import user_has_permission


class HasAppPermission(BasePermission):
    """Check a single permission from the database RBAC tables."""

    permission_name = ''

    def __init__(self, permission_name=None):
        if permission_name:
            self.permission_name = permission_name

    def has_permission(self, request, view):
        perm = getattr(view, 'required_permission', None) or self.permission_name
        if not perm:
            return False
        return user_has_permission(request.user, perm)


class HasAnyAppPermission(BasePermission):
    """Pass if the user has any one of the listed permissions."""

    permission_names = ()

    def __init__(self, *permission_names):
        if permission_names:
            self.permission_names = permission_names

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, 'user_type', None) == 'admin':
            return True
        names = getattr(view, 'required_permissions', None) or self.permission_names
        if not names:
            return False
        return any(user_has_permission(user, p) for p in names)


def require_permission(perm_name):
    """Factory: @permission_classes([IsAuthenticated, require_permission('...')])."""

    class _Perm(HasAppPermission):
        permission_name = perm_name

    return _Perm


def require_any_permission(*perm_names):
    class _Perm(HasAnyAppPermission):
        permission_names = perm_names

    return _Perm


# ── Role gates (RBAC Approach A: permissions from DB, not bare user_type) ──

class IsAdmin(BasePermission):
    """Admin access via system.admin_access (Admin role has all permissions)."""

    def has_permission(self, request, view):
        return user_has_permission(request.user, 'system.admin_access')


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return user_has_permission(request.user, 'faculty.view_own_profile')


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return user_has_permission(request.user, 'students.view_own_profile')


class IsApplicant(BasePermission):
    def has_permission(self, request, view):
        return user_has_permission(request.user, 'admissions.view_own_application')


class IsAdmissionApplicant(BasePermission):
    """Applicant user_type with admission submit/view permissions."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.user_type != 'applicant':
            return False
        return (
            user_has_permission(user, 'admissions.submit_application')
            or user_has_permission(user, 'admissions.view_own_application')
        )


class IsAdminOrTeacher(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return (
            user_has_permission(u, 'system.admin_access')
            or user_has_permission(u, 'faculty.view_own_profile')
        )


class IsAdminOrTeacherOrStudent(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return (
            user_has_permission(u, 'system.admin_access')
            or user_has_permission(u, 'faculty.view_own_profile')
            or user_has_permission(u, 'students.view_own_profile')
        )


class IsSuperuser(BasePermission):
    """Django superuser only — for setup/maintenance APIs not exposed in dashboards."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


class IsFinanceOfficer(BasePermission):
    """Finance officer: user_type finance_officer plus fees RBAC permissions (dual layer)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or user_has_permission(user, 'system.admin_access'):
            return True
        if user.user_type != 'finance_officer':
            return False
        return (
            user_has_permission(user, 'fees.view_fees')
            or user_has_permission(user, 'fees.manage_fees')
        )
