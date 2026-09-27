"""Admissions business rule and API tests."""
from decimal import Decimal

from django.test import TestCase

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department, DegreeProgram
from admissions.models import Applicant, AdmissionApplication, AdmissionSettings
from admissions.views import ADMISSION_FEE_AMOUNT, _program_admission_fee, LOCKED_APPLICATION_STATUSES


class AdmissionFeeTests(TestCase):
    def test_admission_fee_is_fixed(self):
        dept = Department.objects.create(department_code='CS', department_name='Computer Science')
        program = DegreeProgram.objects.create(
            department=dept,
            program_name='BS Computer Science',
            program_code='BSCS',
            degree_level='BS',
            duration_years=4,
            total_semesters=8,
            total_credit_hours=130,
            fee_per_semester=Decimal('50000'),
        )
        self.assertEqual(_program_admission_fee(program), ADMISSION_FEE_AMOUNT)
        self.assertEqual(ADMISSION_FEE_AMOUNT, Decimal('15000'))


class AdmissionProgramsAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='Computer Science')
        self.bs = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
            accepting_admissions=True, is_active=True,
        )
        self.ms = DegreeProgram.objects.create(
            department=dept, program_name='MS CS', program_code='MSCS',
            degree_level='MS', duration_years=2, total_semesters=4, total_credit_hours=60,
            accepting_admissions=True, is_active=True,
        )
        self.applicant = self.create_applicant()
        self.auth_as(self.applicant)

    def test_programs_exclude_postgraduate(self):
        response = self.client.get('/api/admissions/programs/')
        self.assertEqual(response.status_code, 200)
        codes = {p['program_code'] for p in response.data}
        self.assertIn('BSCS', codes)
        self.assertNotIn('MSCS', codes)


class AdminVerifyDocumentBlockedTests(Campus360APITestCase):
    def setUp(self):
        self.admin = self.create_admin()
        dept = Department.objects.create(department_code='CS', department_name='CS')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        applicant_user = self.create_applicant('app2@test.edu', 'app2')
        applicant = Applicant.objects.create(
            user=applicant_user, first_name='Ali', last_name='Khan',
        )
        self.application = AdmissionApplication.objects.create(
            applicant=applicant, program=program, application_number='APP-001',
            status='under_review',
        )
        self.auth_as(self.admin)

    def test_admin_manual_verify_returns_403(self):
        response = self.client.post(
            f'/api/admissions/admin/applications/{self.application.pk}/documents/1/verify/',
            {'verified': True},
            format='json',
        )
        self.assertEqual(response.status_code, 403)


class ApplicationLockTests(TestCase):
    def test_locked_statuses_include_submitted_states(self):
        self.assertIn('pending', LOCKED_APPLICATION_STATUSES)
        self.assertIn('approved', LOCKED_APPLICATION_STATUSES)
        self.assertNotIn('draft', LOCKED_APPLICATION_STATUSES)


class AdmissionSettingsTests(Campus360APITestCase):
    def test_public_settings_accessible(self):
        AdmissionSettings.objects.update_or_create(pk=1, defaults={'is_open': True})
        response = self.client.get('/api/admissions/settings/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_open'])
