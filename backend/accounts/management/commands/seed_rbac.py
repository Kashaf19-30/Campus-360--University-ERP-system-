"""
Seed RBAC roles, permissions, and role-permission mappings.

Run after migrate:
  python manage.py seed_rbac
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Permission, Role, RolePermission, User, UserRole
from accounts.rbac import ensure_user_role_for_type

APP_PERMISSIONS = [
    # System
    ('system.admin_access', 'system', 'admin', 'Full admin access'),
    ('system.view_audit_log', 'system', 'view', 'View audit logs'),
    ('system.manage_role_permissions', 'system', 'manage', 'Manage role permission assignments'),
    # Academics
    ('academics.view_department', 'academics', 'view', 'View departments'),
    ('academics.create_department', 'academics', 'create', 'Create departments'),
    ('academics.update_department', 'academics', 'update', 'Update departments'),
    ('academics.delete_department', 'academics', 'delete', 'Delete departments'),
    ('academics.view_program', 'academics', 'view', 'View programs'),
    ('academics.create_program', 'academics', 'create', 'Create programs'),
    ('academics.update_program', 'academics', 'update', 'Update programs'),
    ('academics.delete_program', 'academics', 'delete', 'Delete programs'),
    ('academics.view_course', 'academics', 'view', 'View courses'),
    ('academics.create_course', 'academics', 'create', 'Create courses'),
    ('academics.update_course', 'academics', 'update', 'Update courses'),
    ('academics.delete_course', 'academics', 'delete', 'Delete courses'),
    ('academics.manage_program_courses', 'academics', 'manage', 'Manage program courses'),
    # Faculty
    ('faculty.view_faculty', 'faculty', 'view', 'View faculty listing'),
    ('faculty.create_faculty', 'faculty', 'create', 'Create faculty credentials'),
    ('faculty.update_faculty', 'faculty', 'update', 'Update faculty'),
    ('faculty.delete_faculty', 'faculty', 'delete', 'Deactivate faculty'),
    ('faculty.view_own_profile', 'faculty', 'view_own', 'View own faculty profile'),
    # Students
    ('students.view_student', 'students', 'view', 'View students'),
    ('students.view_own_profile', 'students', 'view_own', 'View own student profile'),
    ('students.update_student', 'students', 'update', 'Update student records'),
    # Admissions
    ('admissions.view_application', 'admissions', 'view', 'Review applications'),
    ('admissions.decide_application', 'admissions', 'decide', 'Approve/reject applications'),
    ('admissions.submit_application', 'admissions', 'submit', 'Submit application'),
    ('admissions.view_own_application', 'admissions', 'view_own', 'View own application'),
    ('academics.view_offering', 'academics', 'view', 'View course offerings'),
    ('academics.manage_offering', 'academics', 'manage', 'Manage course offerings and teacher assignment'),
    # Enrollments
    ('enrollments.view_enrollment', 'enrollments', 'view', 'View enrollments'),
    ('enrollments.view_own_enrollment', 'enrollments', 'view_own', 'View own enrollment'),
    # Examinations
    ('examinations.view_examination', 'examinations', 'view', 'View examinations'),
    ('examinations.create_examination', 'examinations', 'create', 'Create examinations'),
    ('examinations.update_examination', 'examinations', 'update', 'Update examinations'),
    ('examinations.delete_examination', 'examinations', 'delete', 'Delete examinations'),
    ('examinations.manage_exam_schedule', 'examinations', 'schedule', 'Manage exam schedules'),
    ('examinations.view_marks', 'examinations', 'view_marks', 'View marks'),
    ('examinations.enter_marks', 'examinations', 'enter_marks', 'Enter/upload marks'),
    ('examinations.request_marks_edit', 'examinations', 'request_marks_edit', 'Request marks edit permission'),
    ('examinations.approve_marks_edit', 'examinations', 'approve_marks_edit', 'Approve marks edit requests'),
    ('examinations.view_own_results', 'examinations', 'view_own_results', 'View own results'),
    ('examinations.view_own_grades', 'examinations', 'view_own_grades', 'View own grades'),
    ('examinations.publish_results', 'examinations', 'publish', 'Publish results'),
    # Attendance
    ('attendance.view_attendance', 'attendance', 'view', 'View attendance'),
    ('attendance.mark_attendance', 'attendance', 'mark', 'Mark attendance'),
    ('attendance.view_own_attendance', 'attendance', 'view_own', 'View own attendance'),
    # Complaints
    ('complaints.view_complaint', 'complaints', 'view', 'View all complaints'),
    ('complaints.create_complaint', 'complaints', 'create', 'Submit complaint'),
    ('complaints.view_own_complaint', 'complaints', 'view_own', 'View own complaints'),
    ('complaints.manage_complaint', 'complaints', 'manage', 'Assign/resolve complaints'),
    ('complaints.use_thread', 'complaints', 'thread', 'Use complaint message thread'),
    # Announcements
    ('announcements.view_announcement', 'announcements', 'view', 'View announcements'),
    ('announcements.create_announcement', 'announcements', 'create', 'Create announcements'),
    ('announcements.manage_announcement', 'announcements', 'manage', 'Manage announcements'),
    # Fees
    ('fees.view_fees', 'fees', 'view', 'View fees'),
    ('fees.view_own_fees', 'fees', 'view_own', 'View own fees'),
    ('fees.manage_fees', 'fees', 'manage', 'Manage fee structures'),
    # Credentials
    ('accounts.create_credentials', 'accounts', 'create', 'Create user credentials'),
]

TEACHER_PERMS = {
    'examinations.view_examination', 'examinations.create_examination', 'examinations.update_examination',
    'examinations.manage_exam_schedule', 'examinations.view_marks', 'examinations.enter_marks',
    'examinations.request_marks_edit', 'attendance.view_attendance', 'attendance.mark_attendance',
    'announcements.view_announcement', 'announcements.create_announcement',
    'complaints.create_complaint', 'complaints.view_own_complaint', 'complaints.use_thread',
    'faculty.view_own_profile', 'academics.view_offering', 'students.view_student',
    'enrollments.view_enrollment',
}

STUDENT_PERMS = {
    'examinations.view_own_results', 'examinations.view_own_grades',
    'enrollments.view_own_enrollment',
    'complaints.create_complaint', 'complaints.view_own_complaint', 'complaints.use_thread',
    'announcements.view_announcement', 'students.view_own_profile',
    'fees.view_own_fees', 'attendance.view_own_attendance',
    'admissions.submit_application', 'admissions.view_own_application',
}

STAFF_PERMS = set()  # deprecated — Staff role removed

APPLICANT_PERMS = {
    'admissions.submit_application', 'admissions.view_own_application',
}

FINANCE_PERMS = {
    'fees.view_fees', 'fees.manage_fees', 'admissions.view_application',
}


class Command(BaseCommand):
    help = 'Seed RBAC roles, permissions, and role-permission mappings'

    @transaction.atomic
    def handle(self, *args, **options):
        perm_objs = {}
        for name, module, action, desc in APP_PERMISSIONS:
            p, _ = Permission.objects.update_or_create(
                permission_name=name,
                defaults={'module_name': module, 'action_type': action, 'description': desc},
            )
            perm_objs[name] = p

        roles = {}
        for rname, desc, system in [
            ('Admin', 'System administrator', True),
            ('Teacher', 'Faculty member', True),
            ('Student', 'Enrolled student', True),
            ('Applicant', 'Admission applicant', True),
            ('Finance Officer', 'Finance office staff', True),
        ]:
            role, _ = Role.objects.update_or_create(
                role_name=rname,
                defaults={'description': desc, 'is_system_role': system},
            )
            roles[rname] = role

        RolePermission.objects.filter(role=roles['Admin']).delete()
        for p in perm_objs.values():
            RolePermission.objects.get_or_create(role=roles['Admin'], permission=p)

        mapping = {
            'Teacher': TEACHER_PERMS,
            'Student': STUDENT_PERMS,
            'Applicant': APPLICANT_PERMS,
            'Finance Officer': FINANCE_PERMS,
        }
        for rname, pnames in mapping.items():
            RolePermission.objects.filter(role=roles[rname]).delete()
            for pname in pnames:
                if pname in perm_objs:
                    RolePermission.objects.get_or_create(role=roles[rname], permission=perm_objs[pname])

        synced = 0
        for user in User.objects.filter(is_active=True):
            ensure_user_role_for_type(user)
            synced += 1

        self.stdout.write(self.style.SUCCESS(
            f'RBAC seeded: {len(perm_objs)} permissions, {len(roles)} roles, {synced} users synced'
        ))
