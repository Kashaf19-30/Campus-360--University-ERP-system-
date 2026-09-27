"""Database constraint and referential integrity tests."""
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import Department, DegreeProgram, Semester, Course, ProgramCourse
from enrollments.models import Enrollment
from fees.models import FeeStructure
from students.models import Student


class DatabaseConstraintTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(department_code='DB', department_name='DB Dept')
        self.program = DegreeProgram.objects.create(
            department=self.dept, program_name='BS DB', program_code='BSDB',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.semester = Semester.objects.create(
            semester_name='DB Fall', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(),
        )
        user = User.objects.create_user(email='db@test.edu', username='dbuser', password='pass', user_type='student')
        self.student = Student.objects.create(
            user=user, program=self.program, registration_number='DB-001',
            batch_year=2026, admission_date=timezone.now().date(),
        )

    def test_unique_registration_number(self):
        user2 = User.objects.create_user(email='db2@test.edu', username='dbuser2', password='pass', user_type='student')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create(
                    user=user2, program=self.program, registration_number='DB-001',
                    batch_year=2026, admission_date=timezone.now().date(),
                )

    def test_unique_enrollment_per_student_semester(self):
        Enrollment.objects.create(student=self.student, semester=self.semester)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Enrollment.objects.create(student=self.student, semester=self.semester)

    def test_fee_structure_unique_together(self):
        d = timezone.now().date()
        FeeStructure.objects.create(
            program=self.program, semester_number=1, fee_type='semester_fee',
            amount=Decimal('1000'), effective_from=d,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FeeStructure.objects.create(
                    program=self.program, semester_number=1, fee_type='semester_fee',
                    amount=Decimal('2000'), effective_from=d,
                )

    def test_cascade_delete_student_removes_enrollments(self):
        Enrollment.objects.create(student=self.student, semester=self.semester)
        sid = self.student.pk
        self.student.delete()
        self.assertFalse(Enrollment.objects.filter(student_id=sid).exists())
