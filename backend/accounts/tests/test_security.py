"""Security-focused regression tests."""
from accounts.tests.base import Campus360APITestCase


class IDORAndAccessControlTests(Campus360APITestCase):
    def setUp(self):
        self.applicant = self.create_applicant()
        self.student = self.create_student_user()
        self.admin = self.create_admin()

    def test_no_token_admin_applications_forbidden(self):
        response = self.client.get('/api/admissions/admin/applications/')
        self.assertEqual(response.status_code, 401)

    def test_applicant_cannot_list_all_applications(self):
        self.auth_as(self.applicant)
        response = self.client.get('/api/admissions/admin/applications/')
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_create_department(self):
        self.auth_as(self.student)
        response = self.client.post(
            '/api/academics/departments/create/',
            {'department_name': 'Hack Dept', 'department_code': 'HACK'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_sql_injection_in_login_rejected(self):
        response = self.client.post(
            '/api/auth/login/',
            {'email': "' OR 1=1 --", 'password': 'x'},
            format='json',
        )
        self.assertIn(response.status_code, (400, 401))

    def test_invalid_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)
