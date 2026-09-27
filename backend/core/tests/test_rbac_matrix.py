"""Role × endpoint authorization matrix."""
from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from core.tests.endpoint_registry import ADMIN_ONLY_SENSITIVE, STUDENT_FORBIDDEN, APPLICANT_FORBIDDEN


class RBACMatrixTests(Campus360APITestCase):
    def setUp(self):
        self.admin = make_user('rbac_admin@test.edu', 'rbac_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access'], role_name='Admin')
        self.student = make_user('rbac_stu@test.edu', 'rbac_stu', 'student')
        grant_permissions(self.student, ['students.view_own_profile'], role_name='Student')
        self.applicant = make_user('rbac_app@test.edu', 'rbac_app', 'applicant')
        grant_permissions(self.applicant, [
            'admissions.view_own_application', 'admissions.submit_application',
        ], role_name='Applicant')
        self.teacher = make_user('rbac_tea@test.edu', 'rbac_tea', 'teacher')
        grant_permissions(self.teacher, ['examinations.view_examination'], role_name='Teacher')

    def test_admin_can_access_sensitive_endpoints(self):
        self.auth_as(self.admin)
        for method, path, *rest in ADMIN_ONLY_SENSITIVE:
            body = rest[0] if rest else {}
            r = self.client.post(path, body, format='json') if method == 'POST' else self.client.get(path)
            self.assertIn(r.status_code, (200, 201, 400, 404), f'Admin blocked from {path}: {r.status_code}')

    def test_student_forbidden_from_admin_endpoints(self):
        self.auth_as(self.student)
        for method, path, *rest in STUDENT_FORBIDDEN:
            body = rest[0] if rest else {}
            r = self.client.post(path, body, format='json') if method == 'POST' else self.client.get(path)
            self.assertIn(r.status_code, (403, 404), f'Student allowed {path}: {r.status_code}')

    def test_applicant_forbidden_from_student_admin_endpoints(self):
        self.auth_as(self.applicant)
        for method, path, *rest in APPLICANT_FORBIDDEN:
            body = rest[0] if rest else {}
            r = self.client.post(path, body, format='json') if method == 'POST' else self.client.get(path)
            self.assertIn(r.status_code, (403, 404), f'Applicant allowed {path}: {r.status_code}')

    def test_teacher_without_enter_marks_cannot_enter_marks(self):
        self.auth_as(self.teacher)
        r = self.client.post('/api/examinations/1/marks/enter/', {'marks': []}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_unauthenticated_gets_401(self):
        self.client.credentials()
        r = self.client.get('/api/students/')
        self.assertEqual(r.status_code, 401)
