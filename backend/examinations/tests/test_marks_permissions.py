"""Examination marks permission tests."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department, DegreeProgram, Semester, Course, CourseOffering
from faculty.models import Designation, Faculty
from students.models import Student
from enrollments.models import CourseRegistration, Enrollment
from examinations.models import ExamType, Examination, Marks


class MarksPermissionAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='CS')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.semester = Semester.objects.create(
            semester_name='Fall 2025', academic_year=2025, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date() + timezone.timedelta(days=120),
        )
        course = Course.objects.create(
            department=dept, course_code='CS101', course_name='Intro', credit_hours=3, course_type='core',
        )
        teacher_user = make_user('teacher@test.edu', 'teacher1', 'teacher')
        grant_permissions(teacher_user, ['examinations.view_examination'])
        designation = Designation.objects.create(designation_title='Lecturer')
        faculty = Faculty.objects.create(
            user=teacher_user, department=dept, program=program, designation=designation,
            employee_code='FAC-001', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        offering = CourseOffering.objects.create(
            course=course, semester=self.semester, faculty=faculty,
        )
        exam_type = ExamType.objects.create(
            type_name='Quiz 1', weightage_percentage=10, marks_period='pre_mid',
        )
        self.exam = Examination.objects.create(
            course=course, semester=self.semester, offering=offering, exam_type=exam_type,
            exam_name='Quiz 1', total_marks=10, passing_marks=4,
        )
        self.view_only_teacher = teacher_user
        self.enter_teacher = make_user('teacher2@test.edu', 'teacher2', 'teacher')
        grant_permissions(self.enter_teacher, [
            'examinations.view_examination', 'examinations.enter_marks',
        ])
        enter_faculty = Faculty.objects.create(
            user=self.enter_teacher, department=dept, program=program, designation=designation,
            employee_code='FAC-002', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        self.enter_offering = CourseOffering.objects.create(
            course=course, semester=self.semester, faculty=enter_faculty,
        )
        self.enter_exam = Examination.objects.create(
            course=course, semester=self.semester, offering=self.enter_offering, exam_type=exam_type,
            exam_name='Quiz 1', assessment_category='quiz', weight_percentage=10,
            total_marks=10, passing_marks=4,
        )
        student_user = make_user('student@test.edu', 'student1', 'student')
        self.student = Student.objects.create(
            user=student_user, program=program, registration_number='REG-001',
            batch_year=2025, current_semester=1, admission_date=timezone.now().date(),
        )
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        self.registration = CourseRegistration.objects.create(
            enrollment=enrollment,
            course=course,
            offering=self.enter_offering,
            student=self.student,
            status='registered',
        )

    def test_view_only_teacher_cannot_enter_marks(self):
        self.auth_as(self.view_only_teacher)
        response = self.client.post(
            f'/api/examinations/{self.exam.exam_id}/marks/enter/',
            {'marks': []},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_can_enter_marks_with_registration(self):
        self.auth_as(self.enter_teacher)
        response = self.client.post(
            f'/api/examinations/{self.enter_exam.exam_id}/marks/enter/',
            {'marks': [{'student': self.student.student_id, 'obtained_marks': 8, 'is_absent': False}]},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data['created']), 1)
        mark = Marks.objects.get(exam=self.enter_exam, student=self.student)
        self.assertEqual(float(mark.obtained_marks), 8.0)
        self.assertEqual(mark.registration_id, self.registration.registration_id)

    def test_teacher_cannot_enter_marks_above_exam_total(self):
        self.auth_as(self.enter_teacher)
        response = self.client.post(
            f'/api/examinations/{self.enter_exam.exam_id}/marks/enter/',
            {'marks': [{'student': self.student.student_id, 'obtained_marks': 99, 'is_absent': False}]},
            format='json',
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertTrue(response.data.get('errors'))

    def test_student_can_view_own_assessment_marks(self):
        Marks.objects.create(
            exam=self.enter_exam,
            student=self.student,
            registration=self.registration,
            obtained_marks=7,
            is_absent=False,
            entered_by=Faculty.objects.get(user=self.enter_teacher),
        )
        student_user = self.student.user
        grant_permissions(student_user, ['examinations.view_own_grades'], role_name='StudentMarks')
        self.auth_as(student_user)
        response = self.client.get('/api/examinations/marks/me/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['obtained_marks']), 7.0)

    def test_teacher_can_update_existing_marks(self):
        Marks.objects.create(
            exam=self.enter_exam,
            student=self.student,
            registration=self.registration,
            obtained_marks=5,
            entered_by=self.enter_offering.faculty,
        )
        self.auth_as(self.enter_teacher)
        response = self.client.post(
            f'/api/examinations/{self.enter_exam.exam_id}/marks/enter/',
            {'marks': [{'student': self.student.student_id, 'obtained_marks': 9, 'is_absent': False}]},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        mark = Marks.objects.get(exam=self.enter_exam, student=self.student)
        self.assertEqual(float(mark.obtained_marks), 9.0)
        self.assertEqual(Marks.objects.filter(exam=self.enter_exam, student=self.student).count(), 1)

    def test_teacher_list_exams_requires_offering(self):
        self.auth_as(self.enter_teacher)
        response = self.client.get('/api/examinations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_teacher_list_exams_scoped_to_offering(self):
        self.auth_as(self.enter_teacher)
        response = self.client.get(f'/api/examinations/?offering={self.enter_offering.offering_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['exam_id'], self.enter_exam.exam_id)


class MidFinalDefaultTotalsTests(TestCase):
    def test_compute_weighted_points_for_mid_and_final_totals(self):
        from examinations.assessment_setup import compute_weighted_mark_points

        mid_pts, mid_max = compute_weighted_mark_points(15, 30, 30)
        self.assertEqual(mid_pts, Decimal('15.00'))
        self.assertEqual(mid_max, Decimal('30.00'))

        final_pts, final_max = compute_weighted_mark_points(32, 40, 40)
        self.assertEqual(final_pts, Decimal('32.00'))
        self.assertEqual(final_max, Decimal('40.00'))

    def test_ensure_offering_assessments_uses_30_and_40_totals(self):
        from examinations.assessment_setup import (
            ensure_offering_assessments,
            FIXED_MID_TOTAL_MARKS,
            FIXED_FINAL_TOTAL_MARKS,
        )

        dept = Department.objects.create(department_code='EE', department_name='EE')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS EE', program_code='BSEE',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        semester = Semester.objects.create(
            semester_name='Spring 2026', academic_year=2026, semester_type='spring',
            start_date=timezone.now().date(), end_date=timezone.now().date() + timezone.timedelta(days=120),
        )
        course = Course.objects.create(
            department=dept, course_code='EE101', course_name='Circuits', credit_hours=3, course_type='core',
        )
        teacher_user = make_user('midfinal@test.edu', 'midfinal', 'teacher')
        designation = Designation.objects.create(designation_title='Professor')
        faculty = Faculty.objects.create(
            user=teacher_user, department=dept, program=program, designation=designation,
            employee_code='FAC-MF', qualification='PhD', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        offering = CourseOffering.objects.create(course=course, semester=semester, faculty=faculty)
        ExamType.objects.create(type_name='Mid Term', weightage_percentage=30, marks_period='mid_term')
        ExamType.objects.create(type_name='Final Term', weightage_percentage=40, marks_period='final')

        ensure_offering_assessments(offering)

        mid = Examination.objects.get(offering=offering, assessment_category='mid_term')
        final = Examination.objects.get(offering=offering, assessment_category='final')
        self.assertEqual(mid.total_marks, FIXED_MID_TOTAL_MARKS)
        self.assertEqual(final.total_marks, FIXED_FINAL_TOTAL_MARKS)
        self.assertEqual(mid.total_marks, Decimal('30'))
        self.assertEqual(final.total_marks, Decimal('40'))

    def test_sync_rescales_marks_when_total_changes(self):
        from examinations.assessment_setup import sync_mid_final_exam_defaults

        dept = Department.objects.create(department_code='MA', department_name='Math')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS Math', program_code='BSM',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        semester = Semester.objects.create(
            semester_name='Fall 2026', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date() + timezone.timedelta(days=120),
        )
        course = Course.objects.create(
            department=dept, course_code='MA101', course_name='Calculus', credit_hours=3, course_type='core',
        )
        teacher_user = make_user('sync@test.edu', 'sync', 'teacher')
        designation = Designation.objects.create(designation_title='Lecturer')
        faculty = Faculty.objects.create(
            user=teacher_user, department=dept, program=program, designation=designation,
            employee_code='FAC-SYNC', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        offering = CourseOffering.objects.create(course=course, semester=semester, faculty=faculty)
        mid_type = ExamType.objects.create(type_name='Mid', weightage_percentage=30, marks_period='mid_term')
        exam = Examination.objects.create(
            course=course, semester=semester, offering=offering, exam_type=mid_type,
            exam_name='Mid Term', assessment_category='mid_term', weight_percentage=30,
            total_marks=Decimal('100'), passing_marks=Decimal('50'),
        )
        student_user = make_user('syncstu@test.edu', 'syncstu', 'student')
        student = Student.objects.create(
            user=student_user, program=program, registration_number='REG-SYNC',
            batch_year=2026, current_semester=1, admission_date=timezone.now().date(),
        )
        enrollment = Enrollment.objects.create(student=student, semester=semester)
        registration = CourseRegistration.objects.create(
            enrollment=enrollment, course=course, offering=offering,
            student=student, status='registered',
        )
        mark = Marks.objects.create(
            exam=exam, student=student, registration=registration,
            obtained_marks=Decimal('75'), entered_by=faculty,
        )

        sync_mid_final_exam_defaults(offering)

        exam.refresh_from_db()
        mark.refresh_from_db()
        self.assertEqual(exam.total_marks, Decimal('30'))
        self.assertEqual(mark.obtained_marks, Decimal('22.50'))
