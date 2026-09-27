"""Dashboard module API tests."""
from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions


class DashboardAPITests(Campus360APITestCase):
    def setUp(self):
        self.admin = make_user('dash_admin@test.edu', 'dash_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access'], role_name='Admin')
        self.student = make_user('dash_stu@test.edu', 'dash_stu', 'student')
        grant_permissions(self.student, ['students.view_own_profile'], role_name='Student')

    def test_admin_dashboard_stats(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/dashboard/stats/')
        self.assertEqual(r.status_code, 200)

    def test_student_cannot_access_dashboard_stats(self):
        self.auth_as(self.student)
        r = self.client.get('/api/dashboard/stats/')
        self.assertIn(r.status_code, (403, 404))
