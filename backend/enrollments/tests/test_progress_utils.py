"""Academic progress dashboard helpers."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import Course, CourseOffering, Department, DegreeProgram, ProgramCourse, Semester
from enrollments.models import CourseRegistration, Enrollment
from enrollments.progress_utils import get_semester_progress, get_repeat_progress
from examinations.models import FinalGrade, Grade
from faculty.models import Designation, Faculty
from students.models import Student


class SemesterProgressTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(department_code='PRG', department_name='Progress')
        self.program = DegreeProgram.objects.create(
            department=self.dept, program_name='BS PRG', program_code='PRG',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.semester = Semester.objects.create(
            semester_name='PRG Fall', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=True,
        )
        self.course = Course.objects.create(
            department=self.dept, course_code='PRG101', course_name='Progress Course',
            credit_hours=3, course_type='core',
        )
        ProgramCourse.objects.create(
            program=self.program, course=self.course, semester_number=1, is_core=True,
        )
        teacher = User.objects.create_user(email='prg_tea@test.edu', username='prg_tea', password='p', user_type='teacher')
        des = Designation.objects.create(designation_title='Lec')
        self.faculty = Faculty.objects.create(
            user=teacher, department=self.dept, program=self.program, designation=des,
            employee_code='PRG-F1', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        self.offering = CourseOffering.objects.create(
            course=self.course, semester=self.semester, faculty=self.faculty, marks_locked=True,
        )
        user = User.objects.create_user(email='prg_stu@test.edu', username='prg_stu', password='p', user_type='student')
        self.student = Student.objects.create(
            user=user, program=self.program, registration_number='PRG-001',
            batch_year=2026, admission_date=timezone.now().date(), current_semester=1,
        )
        self.grade = Grade.objects.create(
            grade_letter='A', min_percentage=80, max_percentage=100,
            grade_points=Decimal('4.0'), status='pass',
        )

    def test_completed_registrations_appear_in_semester_progress(self):
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        reg = CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=self.offering,
            student=self.student, status='completed', registration_type='regular',
        )
        FinalGrade.objects.create(
            registration=reg, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=90, total_marks=100, percentage=90,
            grade=self.grade, status='pass',
        )

        progress = get_semester_progress(1, self.semester)

        self.assertEqual(progress['student_count'], 1)
        self.assertEqual(progress['regular_courses_total'], 1)
        self.assertEqual(progress['courses'][0]['course_code'], 'PRG101')
        self.assertEqual(progress['courses'][0]['total_students'], 1)
        self.assertEqual(progress['courses'][0]['graded_students'], 1)

    def test_repeat_progress_only_shows_repeat_registrations(self):
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        repeat_offering = CourseOffering.objects.create(
            course=self.course, semester=self.semester, faculty=self.faculty, repeat_offering=True,
        )
        CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=repeat_offering,
            student=self.student, status='completed', registration_type='repeat',
        )

        sem1 = get_repeat_progress(self.semester, curriculum_semester=1)
        self.assertEqual(len(sem1['items']), 1)
        self.assertEqual(sem1['items'][0]['course_code'], 'PRG101')

        sem2 = get_repeat_progress(self.semester, curriculum_semester=2)
        self.assertEqual(len(sem2['items']), 0)

    def test_completed_repeat_offering_hidden_from_admin_progress(self):
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        repeat_offering = CourseOffering.objects.create(
            course=self.course, semester=self.semester, faculty=self.faculty,
            repeat_offering=True, marks_locked=True,
        )
        reg = CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=repeat_offering,
            student=self.student, status='completed', registration_type='repeat',
        )
        from examinations.models import FinalGrade
        FinalGrade.objects.create(
            registration=reg, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=85, total_marks=100, percentage=85,
            grade=self.grade, status='pass',
        )

        progress = get_repeat_progress(self.semester, curriculum_semester=1)
        self.assertEqual(len(progress['items']), 0)
