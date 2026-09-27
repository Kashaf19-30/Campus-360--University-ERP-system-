"""Shared test helpers for Campus360 API tests."""
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, Role, Permission, RolePermission, UserRole, LoginSession
from accounts.utils import generate_jwt_token


def make_user(email, username, user_type, password='TestPass123!'):
    return User.objects.create_user(
        email=email, username=username, password=password, user_type=user_type,
    )


def grant_permissions(user, permission_names, role_name=None):
    role_name = role_name or f'{user.user_type}_test_role_{user.user_id}'
    role, _ = Role.objects.get_or_create(role_name=role_name, defaults={'description': 'test'})
    for name in permission_names:
        module, _, action = name.partition('.')
        perm, _ = Permission.objects.get_or_create(
            permission_name=name,
            defaults={'module_name': module or 'test', 'action_type': action or 'view', 'description': ''},
        )
        RolePermission.objects.get_or_create(role=role, permission=perm)
    UserRole.objects.get_or_create(user=user, role=role)
    return role


def auth_client(client, user, session_token=None):
    token = session_token or f'session-{user.user_id}-{user.email}'
    LoginSession.objects.update_or_create(
        user=user,
        session_token=token,
        defaults={'expires_at': timezone.now() + timedelta(days=1), 'is_active': True},
    )
    jwt = generate_jwt_token(user, token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {jwt}')
    return client


class Campus360APITestCase(APITestCase):
    """Base case with auth helpers."""

    def auth_as(self, user):
        return auth_client(self.client, user)

    def create_applicant(self, email='applicant@test.edu', username='applicant_test'):
        user = make_user(email, username, 'applicant')
        grant_permissions(user, [
            'admissions.view_own_application',
            'admissions.submit_application',
            'admissions.upload_document',
        ])
        return user

    def create_admin(self, email='admin@test.edu', username='admin_test'):
        user = make_user(email, username, 'admin')
        grant_permissions(user, [
            'admissions.view_application',
            'admissions.review_application',
            'admissions.decide_application',
            'students.view_student',
            'students.create_student',
            'fees.view_fees',
            'fees.manage_fees',
            'system.manage_role_permissions',
        ], role_name='Admin')
        return user

    def create_student_user(self, email='student@test.edu', username='student_test'):
        user = make_user(email, username, 'student')
        grant_permissions(user, ['students.view_own_profile'])
        return user

    def create_finance_officer(self, email='finance@test.edu', username='finance_test'):
        user = make_user(email, username, 'finance_officer')
        grant_permissions(user, ['fees.view_fees', 'fees.mark_payment'])
        return user
