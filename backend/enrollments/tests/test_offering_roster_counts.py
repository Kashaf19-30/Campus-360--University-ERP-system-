"""Teacher offering enrolled count and completed-tab eligibility."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import Course, CourseOffering, Department, DegreeProgram, Semester
from enrollments.models import CourseRegistration, Enrollment
from enrollments.repeat_utils import (
    offering_enrolled_count,
    offering_is_empty_shell,
    offering_teaching_complete,
    roster_eligible_count,
    sync_offering_enrolled_count,
)
from examinations.models import FinalGrade, Grade
from faculty.models import Designation, Faculty
from students.models import Student


class OfferingRosterCountTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(department_code='ORC', department_name='ORC Dept')
        self.program = DegreeProgram.objects.create(
            department=self.dept, program_name='BS ORC', program_code='ORC',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.semester = Semester.objects.create(
            semester_name='ORC Fall', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=True,
        )
        self.course = Course.objects.create(
            department=self.dept, course_code='ORC101', course_name='ORC Course',
            credit_hours=3, course_type='core',
        )
        teacher = User.objects.create_user(email='orc_tea@test.edu', username='orc_tea', password='p', user_type='teacher')
        des = Designation.objects.create(designation_title='Lec')
        self.faculty = Faculty.objects.create(
            user=teacher, department=self.dept, program=self.program, designation=des,
            employee_code='ORC-F1', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, semester=self.semester, faculty=self.faculty,
        )
        user = User.objects.create_user(email='orc_stu@test.edu', username='orc_stu', password='p', user_type='student')
        self.student = Student.objects.create(
            user=user, program=self.program, registration_number='ORC-001',
            batch_year=2026, admission_date=timezone.now().date(), current_semester=1,
        )
        self.enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        self.grade = Grade.objects.create(
            grade_letter='A', min_percentage=80, max_percentage=100,
            grade_points=Decimal('4.0'), status='pass',
        )

    def _registration(self, status='registered'):
        return CourseRegistration.objects.create(
            enrollment=self.enrollment, course=self.course, offering=self.offering,
            student=self.student, status=status, registration_type='regular',
        )

    def test_enrolled_count_includes_completed_registrations(self):
        self._registration(status='completed')
        self.assertEqual(roster_eligible_count(self.offering), 0)
        self.assertEqual(offering_enrolled_count(self.offering), 1)
        sync_offering_enrolled_count(self.offering)
        self.offering.refresh_from_db()
        self.assertEqual(self.offering.enrolled_count, 1)

    def test_teaching_complete_when_graded_and_no_active_roster(self):
        reg = self._registration(status='completed')
        FinalGrade.objects.create(
            registration=reg, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=85, total_marks=100, percentage=85,
            grade=self.grade, status='pass',
        )
        self.assertFalse(self.offering.marks_locked)
        self.assertTrue(offering_teaching_complete(self.offering))

    def test_teaching_complete_when_marks_locked(self):
        self.offering.marks_locked = True
        self.offering.save(update_fields=['marks_locked'])
        self.assertTrue(offering_teaching_complete(self.offering))

    def test_empty_offering_deactivated_on_sync(self):
        self.assertTrue(offering_is_empty_shell(self.offering))
        sync_offering_enrolled_count(self.offering)
        self.offering.refresh_from_db()
        self.assertFalse(self.offering.is_active)
        self.assertFalse(offering_is_empty_shell(self.offering))
