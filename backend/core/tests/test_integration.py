"""Cross-module integration workflow tests."""
from decimal import Decimal

from accounts.tests.base import Campus360APITestCase
from admissions.models import Applicant, AdmissionApplication
from academics.models import Department, DegreeProgram
from recommendation.models import DegreeEligibility, TrendScore


class AdmissionToRecommendationIntegrationTests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='CS')
        self.program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
            is_active=True, accepting_admissions=True,
        )
        DegreeEligibility.objects.create(background='ICS Physics', degree=self.program)
        TrendScore.objects.create(background='ICS Physics', degree=self.program, score=8)
        self.applicant_user = self.create_applicant()
        Applicant.objects.create(
            user=self.applicant_user, first_name='Sara', last_name='Ahmed', cnic='3520212345671',
        )

    def test_ai_recommendation_then_application_list_access(self):
        self.auth_as(self.applicant_user)
        profile_resp = self.client.put(
            '/api/recommendations/profile/update/',
            {
                'educational_background': 'ICS Physics',
                'marks': [{'subject_name': 'Physics', 'marks_obtained': 160, 'total_marks': 200}],
                'interest_names': ['Programming & Technology'],
            },
            format='json',
        )
        self.assertEqual(profile_resp.status_code, 200)
        results_resp = self.client.get('/api/recommendations/results/')
        self.assertEqual(results_resp.status_code, 200)
        self.assertTrue(any(r['program_code'] == 'BSCS' for r in results_resp.data))
        apps_resp = self.client.get('/api/admissions/application/')
        self.assertEqual(apps_resp.status_code, 200)


class FinanceAdmissionIntegrationTests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='CS')
        self.program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.applicant_user = self.create_applicant('int@test.edu', 'int_app')
        applicant = Applicant.objects.create(
            user=self.applicant_user, first_name='Test', last_name='User',
        )
        self.application = AdmissionApplication.objects.create(
            applicant=applicant, program=self.program, application_number='INT-001',
            status='challan_pending', admission_challan_amount=Decimal('15000'),
        )
        self.finance = self.create_finance_officer()

    def test_finance_can_mark_admission_paid(self):
        self.auth_as(self.finance)
        response = self.client.post(
            f'/api/fees/finance/admissions/{self.application.pk}/mark-paid/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertTrue(self.application.challan_paid)
