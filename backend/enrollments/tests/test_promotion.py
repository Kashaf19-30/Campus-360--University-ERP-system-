"""Enrollment and promotion business logic tests."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import Department, DegreeProgram, Semester, Course, ProgramCourse, AcademicPolicy
from students.models import Student
from enrollments.models import Enrollment, CourseRegistration
from enrollments.promotion import _semester_fee_paid, get_student_semester_credit_summary
from fees.models import Challan


class PromotionHelperTests(TestCase):
    def setUp(self):
        AcademicPolicy.objects.get_or_create(
            defaults={
                'min_sgpa_pass': Decimal('2.0'),
                'max_semester_credit_hours': 21,
            },
        )
        dept = Department.objects.create(department_code='CS', department_name='CS')
        self.program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.semester = Semester.objects.create(
            semester_name='Fall 2025', academic_year=2025, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(),
        )
        user = User.objects.create_user(
            email='stu@test.edu', username='stu1', password='pass', user_type='student',
        )
        self.student = Student.objects.create(
            user=user, program=self.program, registration_number='REG-001',
            batch_year=2025, admission_date=timezone.now().date(), current_semester=1,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, semester=self.semester, total_credit_hours_registered=3,
        )
        self.course = Course.objects.create(
            department=dept, course_code='CS101', course_name='Intro CS',
            credit_hours=3, course_type='core',
        )
        ProgramCourse.objects.create(
            program=self.program, course=self.course, semester_number=1, is_core=True,
        )

    def test_semester_fee_paid_when_challan_paid(self):
        admin = User.objects.create_user(
            email='admin@test.edu', username='admin1', password='pass', user_type='admin',
        )
        Challan.objects.create(
            challan_number='CH-001', student=self.student, semester=self.semester,
            due_date=timezone.now().date(), total_amount=Decimal('50000'),
            status='paid', generated_by=admin,
        )
        self.assertTrue(_semester_fee_paid(self.student, self.semester))

    def test_semester_fee_unpaid_without_challan(self):
        self.assertFalse(_semester_fee_paid(self.student, self.semester))

    def test_credit_summary_respects_cap(self):
        summary = get_student_semester_credit_summary(self.student, self.semester)
        self.assertEqual(summary['max_semester_credit_hours'], 21)
        self.assertGreaterEqual(summary['remaining_credit_hours'], 0)
