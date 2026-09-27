"""Security and RBAC regression tests."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User, Role, Permission, RolePermission, UserRole, LoginSession
from accounts.utils import generate_jwt_token, create_login_session
from accounts.rbac_policy import validate_role_permission_update
from django.utils import timezone
from datetime import timedelta


class RBACPolicyTests(TestCase):
    def setUp(self):
        self.teacher_role = Role.objects.create(role_name='Teacher', description='Teacher')
        Permission.objects.create(
            permission_name='examinations.view_examination',
            module_name='examinations', action_type='view', description='',
        )
        Permission.objects.create(
            permission_name='system.admin_access',
            module_name='system', action_type='admin', description='',
        )

    def test_blocks_privileged_permission_for_teacher(self):
        ok, err = validate_role_permission_update(
            self.teacher_role, ['examinations.view_examination', 'system.admin_access']
        )
        self.assertFalse(ok)
        self.assertIn('privileged', err)

    def test_blocks_removing_minimum_teacher_permissions(self):
        ok, err = validate_role_permission_update(self.teacher_role, ['examinations.view_examination'])
        self.assertFalse(ok)
        self.assertIn('required permissions', err)


class SessionBoundJWTTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='teacher@test.edu', username='teacher1', password='pass12345', user_type='teacher'
        )
        role = Role.objects.create(role_name='Teacher')
        UserRole.objects.create(user=self.user, role=role)
        self.client = APIClient()

    def _login_token(self):
        session = LoginSession.objects.create(
            user=self.user,
            session_token='test-session-token',
            expires_at=timezone.now() + timedelta(days=1),
        )
        return generate_jwt_token(self.user, session.session_token)

    def test_logout_revokes_jwt(self):
        token = self._login_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 200)

        me = self.client.get('/api/auth/me/')
        self.assertEqual(me.status_code, 401)

    def test_token_without_sid_rejected(self):
        import jwt
        from django.conf import settings
        payload = {
            'user_id': self.user.user_id,
            'email': self.user.email,
            'user_type': self.user.user_type,
            'exp': timezone.now() + timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)


class ApplicantAccessTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            email='app@test.edu', username='applicant1', password='pass12345', user_type='applicant'
        )
        self.student = User.objects.create_user(
            email='stu@test.edu', username='student1', password='pass12345', user_type='student'
        )
        applicant_role = Role.objects.create(role_name='Applicant')
        for name in ('admissions.submit_application', 'admissions.view_own_application'):
            perm, _ = Permission.objects.get_or_create(
                permission_name=name,
                defaults={'module_name': 'admissions', 'action_type': 'view', 'description': ''},
            )
            RolePermission.objects.create(role=applicant_role, permission=perm)
        UserRole.objects.create(user=self.applicant, role=applicant_role)

        self.client = APIClient()

    def _auth(self, user):
        session = LoginSession.objects.create(
            user=user,
            session_token=f'session-{user.user_id}',
            expires_at=timezone.now() + timedelta(days=1),
        )
        token = generate_jwt_token(user, session.session_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_student_cannot_access_applicant_profile(self):
        self._auth(self.student)
        response = self.client.get('/api/admissions/profile/')
        self.assertEqual(response.status_code, 403)

    def test_applicant_can_access_profile(self):
        self._auth(self.applicant)
        response = self.client.get('/api/admissions/profile/')
        self.assertIn(response.status_code, (200, 404))


class RolePermissionsAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.edu', username='admin1', password='pass12345', user_type='admin'
        )
        admin_role = Role.objects.create(role_name='Admin')
        perm, _ = Permission.objects.get_or_create(
            permission_name='system.manage_role_permissions',
            defaults={'module_name': 'system', 'action_type': 'manage', 'description': ''},
        )
        RolePermission.objects.create(role=admin_role, permission=perm)
        UserRole.objects.create(user=self.admin, role=admin_role)

        self.teacher_role = Role.objects.create(role_name='Teacher')
        for name in (
            'examinations.view_examination', 'faculty.view_own_profile', 'academics.view_offering',
            'attendance.mark_attendance', 'attendance.view_attendance',
        ):
            p, _ = Permission.objects.get_or_create(
                permission_name=name,
                defaults={'module_name': 'x', 'action_type': 'view', 'description': ''},
            )
            RolePermission.objects.create(role=self.teacher_role, permission=p)

        self.client = APIClient()
        session = LoginSession.objects.create(
            user=self.admin,
            session_token='admin-session',
            expires_at=timezone.now() + timedelta(days=1),
        )
        token = generate_jwt_token(self.admin, session.session_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_cannot_strip_teacher_below_minimum(self):
        response = self.client.put(
            f'/api/roles/{self.teacher_role.role_id}/permissions/',
            {'permission_names': ['examinations.view_examination']},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('required permissions', response.data['error'])
