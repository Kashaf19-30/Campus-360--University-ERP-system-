"""Integration tests for enrollment, promotion, admission→student flows."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import (
    AcademicPolicy, Department, DegreeProgram, Semester, Course,
    ProgramCourse, CourseOffering,
)
from admissions.models import Applicant, AdmissionApplication
from admissions.views import _register_approved_student
from enrollments.models import Enrollment, CourseRegistration
from enrollments.promotion import enroll_student_for_semester, promote_student_after_published_result
from examinations.models import Result
from faculty.models import Designation, Faculty, FacultyCourseAssignment
from fees.models import Challan, FeeStructure
from students.models import Student
from students.degree_audit import run_degree_audit


class TestDataMixin:
    """Minimal ERP graph for enrollment/promotion integration tests."""

    def _build_academic_graph(self):
        AcademicPolicy.objects.get_or_create(defaults={'max_semester_credit_hours': 21})
        self.dept = Department.objects.create(department_code='TST', department_name='Test CS')
        self.program = DegreeProgram.objects.create(
            department=self.dept, program_name='BS Test CS', program_code='TSTCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
            fee_per_semester=Decimal('50000'), is_active=True,
        )
        self.semester = Semester.objects.create(
            semester_name='Test Fall 2026', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=True,
        )
        self.course = Course.objects.create(
            department=self.dept, course_code='TST101', course_name='Intro Test',
            credit_hours=3, course_type='core',
        )
        ProgramCourse.objects.create(
            program=self.program, course=self.course, semester_number=1, is_core=True,
        )
        self.course2 = Course.objects.create(
            department=self.dept, course_code='TST102', course_name='Data Structures',
            credit_hours=3, course_type='core',
        )
        ProgramCourse.objects.create(
            program=self.program, course=self.course2, semester_number=2, is_core=True,
        )
        FeeStructure.objects.create(
            program=self.program, semester_number=1, fee_type='semester_fee',
            amount=Decimal('50000'), effective_from=timezone.now().date(),
        )
        admin = User.objects.create_user(
            email='admin_int@test.edu', username='admin_int', password='pass', user_type='admin',
        )
        teacher_user = User.objects.create_user(
            email='teacher_int@test.edu', username='teacher_int', password='pass', user_type='teacher',
        )
        designation = Designation.objects.create(designation_title='Lecturer Test')
        self.faculty = Faculty.objects.create(
            user=teacher_user, department=self.dept, program=self.program,
            designation=designation, employee_code='TST-FAC-1',
            qualification='MS', joining_date=timezone.now().date(), employment_type='permanent',
        )
        FacultyCourseAssignment.objects.create(
            faculty=self.faculty, program=self.program, course=self.course, is_active=True,
        )
        FacultyCourseAssignment.objects.create(
            faculty=self.faculty, program=self.program, course=self.course2, is_active=True,
        )
        CourseOffering.objects.create(
            course=self.course, semester=self.semester, faculty=self.faculty,
        )
        CourseOffering.objects.create(
            course=self.course2, semester=self.semester, faculty=self.faculty,
        )
        self.admin = admin

    def _make_student(self, sem=1):
        user = User.objects.create_user(
            email=f'stu_{sem}@test.edu', username=f'stu_{sem}', password='pass', user_type='student',
        )
        return Student.objects.create(
            user=user, program=self.program,
            registration_number=f'TSTCS-2026-{sem:04d}',
            batch_year=2026, admission_date=timezone.now().date(), current_semester=sem,
        )


class AdmissionToStudentIntegrationTests(TestDataMixin, TestCase):
    def setUp(self):
        self._build_academic_graph()

    def test_approved_application_creates_student_and_switches_role(self):
        app_user = User.objects.create_user(
            email='applicant_int@test.edu', username='applicant_int', password='pass', user_type='applicant',
        )
        applicant = Applicant.objects.create(
            user=app_user, first_name='Test', last_name='Applicant', cnic='3520212345672',
        )
        application = AdmissionApplication.objects.create(
            applicant=applicant, program=self.program,
            application_number='APP-INT-001', status='approved', challan_paid=True,
        )
        result = _register_approved_student(application, self.admin)
        self.assertNotIn('error', result)
        student = result['student']
        self.assertTrue(Student.objects.filter(pk=student.pk).exists())
        app_user.refresh_from_db()
        application.refresh_from_db()
        self.assertEqual(app_user.user_type, 'student')
        self.assertEqual(application.status, 'registered')


class SemesterFeePromotionIntegrationTests(TestDataMixin, TestCase):
    def setUp(self):
        self._build_academic_graph()
        self.student = self._make_student(sem=1)

    def test_enrollment_blocked_without_semester_fee(self):
        stats = enroll_student_for_semester(self.student, self.semester, self.admin)
        self.assertTrue(stats.get('registration_blocked'))
        self.assertEqual(stats['enrolled_courses'], [])
        self.assertFalse(
            CourseRegistration.objects.filter(student=self.student).exists(),
        )
        self.assertTrue(
            Challan.objects.filter(student=self.student, semester=self.semester).exists(),
        )

    def test_enrollment_succeeds_after_semester_fee_paid(self):
        Challan.objects.create(
            challan_number='CH-INT-001', student=self.student, semester=self.semester,
            due_date=timezone.now().date(), total_amount=Decimal('50000'),
            status='paid', generated_by=self.admin,
        )
        stats = enroll_student_for_semester(self.student, self.semester, self.admin)
        self.assertNotIn('registration_blocked', stats)
        self.assertGreater(len(stats['enrolled_courses']), 0)
        self.assertTrue(
            CourseRegistration.objects.filter(
                student=self.student, course=self.course, status='registered',
            ).exists(),
        )

    def test_promotion_blocked_without_fee_then_succeeds_after_payment(self):
        """Published result → promotion blocked until semester fee is paid."""
        result = Result.objects.create(
            student=self.student, semester=self.semester,
            sgpa=Decimal('3.20'), cgpa=Decimal('3.20'),
            total_credit_hours_attempted=3, total_credit_hours_earned=3,
            status='pass', is_published=True,
        )

        # No paid challan → promotion deferred
        promo = promote_student_after_published_result(self.student, self.semester, self.admin)
        self.assertFalse(promo['promoted'])
        self.assertTrue(promo.get('promotion_pending'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.current_semester, 1)

        # Pay fee → pending promotion completes automatically (no second admin click)
        Challan.objects.filter(student=self.student, semester=self.semester).update(
            status='paid', curriculum_semester=2,
        )
        if not Challan.objects.filter(student=self.student, semester=self.semester, status='paid').exists():
            Challan.objects.create(
                challan_number='CH-INT-PROMO', student=self.student, semester=self.semester,
                curriculum_semester=2,
                due_date=timezone.now().date(), total_amount=Decimal('50000'),
                status='paid', generated_by=self.admin,
            )
        from enrollments.promotion import try_complete_pending_promotion
        promo2 = try_complete_pending_promotion(self.student, self.semester, 2, self.admin)
        self.assertTrue(promo2.get('promoted'), promo2)
        self.student.refresh_from_db()
        self.assertEqual(self.student.current_semester, 2)
        result.refresh_from_db()
        self.assertTrue(result.promotion_applied)
        self.assertFalse(result.promotion_pending)


class DegreeAuditIntegrationTests(TestDataMixin, TestCase):
    def setUp(self):
        self._build_academic_graph()
        self.student = self._make_student(sem=8)

    def test_degree_audit_runs_for_student(self):
        audit = run_degree_audit(self.student)
        self.assertIn('eligible', audit)
        self.assertIn('missing_courses', audit)
