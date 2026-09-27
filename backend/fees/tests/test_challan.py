"""Fee and challan API tests."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.tests.base import Campus360APITestCase
from academics.models import Department, DegreeProgram, Semester
from students.models import Student
from fees.models import FeeStructure, Challan


class FeeStructureTests(TestCase):
    def test_unique_per_program_semester_date(self):
        dept = Department.objects.create(department_code='CS', department_name='CS')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        effective = timezone.now().date()
        FeeStructure.objects.create(
            program=program, semester_number=1, fee_type='semester_fee',
            amount=Decimal('45000'), effective_from=effective,
        )
        with self.assertRaises(Exception):
            FeeStructure.objects.create(
                program=program, semester_number=1, fee_type='semester_fee',
                amount=Decimal('50000'), effective_from=effective,
            )


class FinanceAuthorizationTests(Campus360APITestCase):
    def setUp(self):
        self.applicant = self.create_applicant()
        self.finance = self.create_finance_officer()
        self.student_user = self.create_student_user()

    def test_applicant_cannot_mark_challan_paid(self):
        self.auth_as(self.applicant)
        response = self.client.post('/api/fees/finance/challans/1/mark-paid/', {}, format='json')
        self.assertIn(response.status_code, (403, 404))

    def test_student_cannot_access_finance_dashboard(self):
        self.auth_as(self.student_user)
        response = self.client.get('/api/fees/finance/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_finance_can_access_dashboard(self):
        self.auth_as(self.finance)
        response = self.client.get('/api/fees/finance/dashboard/')
        self.assertEqual(response.status_code, 200)
