"""IDOR — users must not access other users' private resources."""
from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from admissions.models import Applicant, AdmissionApplication
from academics.models import Department, DegreeProgram
from students.models import Student


class IDORTests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='IDOR', department_name='IDOR Dept')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS IDOR', program_code='IDOR',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.applicant_a = self.create_applicant('applicant_a@test.edu', 'app_a')
        self.applicant_b = self.create_applicant('applicant_b@test.edu', 'app_b')
        Applicant.objects.create(user=self.applicant_a, first_name='A', last_name='One')
        Applicant.objects.create(user=self.applicant_b, first_name='B', last_name='Two')
        AdmissionApplication.objects.create(
            applicant=Applicant.objects.get(user=self.applicant_a),
            program=program, application_number='APP-A-001', status='draft',
        )

        self.student_a = make_user('stu_a@test.edu', 'stu_a', 'student')
        grant_permissions(self.student_a, ['students.view_own_profile'], role_name='StudentA')
        Student.objects.create(
            user=self.student_a, program=program, registration_number='IDOR-001',
            batch_year=2026, admission_date='2026-01-01', current_semester=1,
        )
        self.student_b = make_user('stu_b@test.edu', 'stu_b', 'student')
        grant_permissions(self.student_b, ['students.view_own_profile'], role_name='StudentB')
        Student.objects.create(
            user=self.student_b, program=program, registration_number='IDOR-002',
            batch_year=2026, admission_date='2026-01-01', current_semester=1,
        )

        self.admin = self.create_admin()

    def test_applicant_b_cannot_see_applicant_a_admin_application(self):
        self.auth_as(self.applicant_b)
        r = self.client.get('/api/admissions/admin/applications/1/')
        self.assertEqual(r.status_code, 403)

    def test_student_b_cannot_fetch_student_a_by_id_without_admin_perm(self):
        self.auth_as(self.student_b)
        student_a = Student.objects.get(registration_number='IDOR-001')
        r = self.client.get(f'/api/students/{student_a.pk}/')
        self.assertIn(r.status_code, (403, 404))

    def test_applicant_cannot_access_other_role_student_me(self):
        self.auth_as(self.applicant_a)
        r = self.client.get('/api/students/me/')
        self.assertIn(r.status_code, (403, 404))
