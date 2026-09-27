"""Shared authorization helpers for object-level access checks."""
from accounts.rbac import user_has_permission


def user_is_admin(user) -> bool:
    return user_has_permission(user, 'system.admin_access')


def get_faculty_profile(user):
    try:
        return user.faculty_profile
    except Exception:
        return None


def teacher_owns_offering(user, offering) -> bool:
    faculty = get_faculty_profile(user)
    return bool(faculty and offering.faculty_id == faculty.faculty_id)


def can_view_offering_roster(user, offering) -> bool:
    if user_is_admin(user):
        return user_has_permission(user, 'students.view_student')
    if user.user_type == 'teacher':
        return teacher_owns_offering(user, offering) and user_has_permission(
            user, 'academics.view_offering'
        )
    return False


# Legacy aliases during transition
teacher_owns_section = teacher_owns_offering
can_view_section_roster = can_view_offering_roster


def can_view_complaint(user, complaint) -> bool:
    if user_has_permission(user, 'complaints.view_complaint') or user_has_permission(
        user, 'complaints.manage_complaint'
    ):
        return True
    if complaint.submitted_by_id == user.user_id:
        return user_has_permission(user, 'complaints.view_own_complaint')
    return False


def can_use_complaint_thread(user, complaint) -> bool:
    if user_has_permission(user, 'complaints.manage_complaint'):
        return True
    if complaint.submitted_by_id == user.user_id:
        return user_has_permission(user, 'complaints.use_thread')
    return False
