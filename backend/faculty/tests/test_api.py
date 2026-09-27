"""Faculty module API tests."""
from django.utils import timezone

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department, DegreeProgram
from faculty.models import Designation, Faculty


class FacultyAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='FAC', department_name='Fac Dept')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS Fac', program_code='FAC',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.teacher = make_user('fac_tea@test.edu', 'fac_tea', 'teacher')
        grant_permissions(self.teacher, [
            'faculty.view_own_profile', 'academics.view_offering',
        ], role_name='Teacher')
        des = Designation.objects.create(designation_title='Lecturer')
        Faculty.objects.create(
            user=self.teacher, department=dept, program=program, designation=des,
            employee_code='FAC-001', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        self.admin = make_user('fac_admin@test.edu', 'fac_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access', 'faculty.view_faculty'], role_name='Admin')

    def test_teacher_can_access_me(self):
        self.auth_as(self.teacher)
        r = self.client.get('/api/faculty/me/')
        self.assertEqual(r.status_code, 200)

    def test_admin_can_list_faculty(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/faculty/')
        self.assertEqual(r.status_code, 200)

    def test_teacher_cannot_create_faculty(self):
        self.auth_as(self.teacher)
        r = self.client.post('/api/faculty/create/', {}, format='json')
        self.assertEqual(r.status_code, 403)
