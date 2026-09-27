"""Academics module API tests."""
from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department


class AcademicsAPITests(Campus360APITestCase):
    def setUp(self):
        self.admin = make_user('acad_admin@test.edu', 'acad_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access'], role_name='Admin')
        self.student = make_user('acad_stu@test.edu', 'acad_stu', 'student')
        grant_permissions(self.student, ['students.view_own_profile'], role_name='Student')

    def test_list_departments_public_to_admin(self):
        Department.objects.create(department_code='AC1', department_name='Academics Test')
        self.auth_as(self.admin)
        r = self.client.get('/api/academics/departments/')
        self.assertEqual(r.status_code, 200)

    def test_student_cannot_create_department(self):
        self.auth_as(self.student)
        r = self.client.post('/api/academics/departments/create/', {
            'department_name': 'Hack', 'department_code': 'HCK',
        }, format='json')
        self.assertEqual(r.status_code, 403)

    def test_get_current_semester(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/academics/semesters/current/')
        self.assertIn(r.status_code, (200, 404))

    def test_academic_policy_get(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/academics/policy/')
        self.assertEqual(r.status_code, 200)
