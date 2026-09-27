"""Students module API tests."""
from django.utils import timezone

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department, DegreeProgram
from students.models import Student


class StudentsAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='STU', department_name='Stu Dept')
        self.program = DegreeProgram.objects.create(
            department=dept, program_name='BS Stu', program_code='STU',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.admin = make_user('stu_admin@test.edu', 'stu_admin', 'admin')
        grant_permissions(self.admin, ['system.admin_access', 'students.view_student'], role_name='Admin')
        self.student_user = make_user('stu_me@test.edu', 'stu_me', 'student')
        grant_permissions(self.student_user, ['students.view_own_profile'], role_name='Student')
        Student.objects.create(
            user=self.student_user, program=self.program, registration_number='STU-001',
            batch_year=2026, admission_date=timezone.now().date(),
        )

    def test_student_can_access_me(self):
        self.auth_as(self.student_user)
        r = self.client.get('/api/students/me/')
        self.assertEqual(r.status_code, 200)

    def test_admin_can_list_students(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/students/')
        self.assertEqual(r.status_code, 200)

    def test_student_cannot_list_all_students(self):
        self.auth_as(self.student_user)
        r = self.client.get('/api/students/')
        self.assertEqual(r.status_code, 403)

    def test_degree_audit_me(self):
        self.auth_as(self.student_user)
        r = self.client.get('/api/students/me/degree-audit/')
        self.assertIn(r.status_code, (200, 404))
