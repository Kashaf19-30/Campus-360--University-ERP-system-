"""RBAC permission resolution regression tests."""
from django.test import TestCase

from accounts.models import User, Role, Permission, RolePermission, UserRole
from accounts.rbac import user_has_permission, get_user_permission_names


class RbacLegacyFallbackTests(TestCase):
    def test_teacher_without_role_uses_legacy_permissions(self):
        user = User.objects.create_user(
            email='legacy@test.edu', username='legacy_teacher', password='pass', user_type='teacher',
        )
        self.assertTrue(user_has_permission(user, 'examinations.enter_marks'))

    def test_teacher_with_restricted_role_does_not_inherit_legacy(self):
        user = User.objects.create_user(
            email='restricted@test.edu', username='restricted_teacher', password='pass', user_type='teacher',
        )
        role = Role.objects.create(role_name='ViewOnlyTeacher')
        perm, _ = Permission.objects.get_or_create(
            permission_name='examinations.view_examination',
            defaults={'module_name': 'examinations', 'action_type': 'view', 'description': ''},
        )
        RolePermission.objects.create(role=role, permission=perm)
        UserRole.objects.create(user=user, role=role)
        perms = get_user_permission_names(user)
        self.assertIn('examinations.view_examination', perms)
        self.assertNotIn('examinations.enter_marks', perms)
        self.assertFalse(user_has_permission(user, 'examinations.enter_marks'))
