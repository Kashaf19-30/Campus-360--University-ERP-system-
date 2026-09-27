"""Tests for auto-split course offerings when a new curriculum cohort enrolls."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import (
    AcademicPolicy, Department, DegreeProgram, Semester, Course,
    ProgramCourse, CourseOffering,
)
from enrollments.models import CourseRegistration, Enrollment
from enrollments.promotion import enroll_student_for_semester, _register_course
from faculty.assignment_utils import (
    offering_is_reusable_for_enrollment,
    pick_offering_for_student,
)
from faculty.models import Designation, Faculty, FacultyCourseAssignment
from fees.models import Challan
from students.models import Student


class OfferingCohortSplitTests(TestCase):
    def setUp(self):
        AcademicPolicy.objects.get_or_create(defaults={'max_semester_credit_hours': 21})
        self.dept = Department.objects.create(department_code='SPL', department_name='Split CS')
        self.program = DegreeProgram.objects.create(
            department=self.dept, program_name='BS Split CS', program_code='SPLCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
            fee_per_semester=Decimal('50000'), is_active=True,
        )
        self.semester = Semester.objects.create(
            semester_name='Split Fall 2026', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=True,
        )
        self.course = Course.objects.create(
            department=self.dept, course_code='SPL101', course_name='Intro Split',
            credit_hours=3, course_type='core',
        )
        ProgramCourse.objects.create(
            program=self.program, course=self.course, semester_number=1, is_core=True,
        )
        teacher_user = User.objects.create_user(
            email='teacher_split@test.edu', username='teacher_split', password='pass', user_type='teacher',
        )
        designation = Designation.objects.create(designation_title='Lecturer Split')
        self.faculty = Faculty.objects.create(
            user=teacher_user, department=self.dept, program=self.program,
            designation=designation, employee_code='SPL-FAC-1',
            qualification='MS', joining_date=timezone.now().date(), employment_type='permanent',
        )
        FacultyCourseAssignment.objects.create(
            faculty=self.faculty, program=self.program, course=self.course, is_active=True,
        )
        self.admin = User.objects.create_user(
            email='admin_split@test.edu', username='admin_split', password='pass', user_type='admin',
        )

    def _make_student(self, suffix, sem=1):
        user = User.objects.create_user(
            email=f'stu_{suffix}@split.edu', username=f'stu_{suffix}', password='pass', user_type='student',
        )
        return Student.objects.create(
            user=user, program=self.program,
            registration_number=f'SPLCS-2026-{suffix}',
            batch_year=2026, admission_date=timezone.now().date(), current_semester=sem,
        )

    def _pay_and_enroll(self, student):
        Challan.objects.create(
            challan_number=f'CH-SPL-{student.registration_number}',
            student=student, semester=self.semester,
            due_date=timezone.now().date(), total_amount=Decimal('50000'),
            status='paid', generated_by=self.admin,
        )
        return enroll_student_for_semester(student, self.semester, self.admin)

    def test_same_cohort_reuses_offering(self):
        s1 = self._make_student('0001')
        s2 = self._make_student('0002')
        self._pay_and_enroll(s1)
        self._pay_and_enroll(s2)

        offerings = CourseOffering.objects.filter(course=self.course, repeat_offering=False)
        self.assertEqual(offerings.count(), 1)
        regs = CourseRegistration.objects.filter(course=self.course, status='registered')
        self.assertEqual(regs.count(), 2)
        self.assertEqual(regs.filter(offering=offerings.first()).count(), 2)

    def test_new_sem1_intake_splits_after_prior_cohort_promoted(self):
        batch_a = [self._make_student(f'A{i:02d}') for i in range(1, 6)]
        for student in batch_a:
            self._pay_and_enroll(student)

        first_offering = CourseOffering.objects.get(course=self.course, cohort_sequence=1)
        for student in batch_a:
            reg = CourseRegistration.objects.get(student=student, course=self.course)
            reg.status = 'completed'
            reg.save(update_fields=['status'])
            student.current_semester = 2
            student.save(update_fields=['current_semester'])

        self.assertFalse(offering_is_reusable_for_enrollment(first_offering, 1))

        batch_b = [self._make_student(f'B{i:02d}') for i in range(1, 6)]
        for student in batch_b:
            self._pay_and_enroll(student)

        offerings = CourseOffering.objects.filter(
            course=self.course, repeat_offering=False,
        ).order_by('cohort_sequence')
        self.assertEqual(offerings.count(), 2)
        second_offering = offerings.last()
        self.assertEqual(second_offering.cohort_sequence, 2)
        self.assertNotEqual(first_offering.pk, second_offering.pk)

        new_regs = CourseRegistration.objects.filter(
            student__in=batch_b, course=self.course, status='registered',
        )
        self.assertEqual(new_regs.count(), 5)
        self.assertTrue(all(r.offering_id == second_offering.pk for r in new_regs))

        old_regs = CourseRegistration.objects.filter(
            student__in=batch_a, course=self.course,
        )
        self.assertTrue(all(r.offering_id == first_offering.pk for r in old_regs))

    def test_pick_offering_creates_second_shell_when_first_is_historical(self):
        student_old = self._make_student('OLD1')
        self._pay_and_enroll(student_old)
        offering_old = CourseRegistration.objects.get(
            student=student_old, course=self.course,
        ).offering
        reg = CourseRegistration.objects.get(student=student_old, course=self.course)
        reg.status = 'completed'
        reg.save(update_fields=['status'])
        student_old.current_semester = 2
        student_old.save(update_fields=['current_semester'])

        student_new = self._make_student('NEW1')
        warnings = []
        offering_new = pick_offering_for_student(
            self.course, self.program, self.semester, student_new, warnings,
            curriculum_semester=1,
        )
        self.assertIsNotNone(offering_new)
        self.assertNotEqual(offering_old.pk, offering_new.pk)
        self.assertEqual(offering_new.cohort_sequence, 2)

        enrollment = Enrollment.objects.create(
            student=student_new, semester=self.semester, status='enrolled',
        )
        _register_course(enrollment, student_new, self.course, offering_new, registration_type='regular')
        self.assertEqual(
            CourseRegistration.objects.get(student=student_new, course=self.course).offering_id,
            offering_new.pk,
        )
