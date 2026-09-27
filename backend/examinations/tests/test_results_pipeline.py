"""Results pipeline and publish → promotion integration tests."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from academics.models import AcademicPolicy, Department, DegreeProgram, Semester, Course, ProgramCourse, CourseOffering
from enrollments.models import Enrollment, CourseRegistration
from enrollments.promotion import enroll_student_for_semester, promote_student_after_published_result
from examinations.models import ExamType, Examination, FinalGrade, Grade, Marks, Result
from examinations.results_pipeline import (
    compute_offering_final_grades,
    generate_results_for_semester,
    compute_student_sgpa,
    compute_student_cgpa,
    ensure_semester_result,
    refresh_student_academic_record,
    refresh_students_after_offering_grades,
)
from academics.policy_utils import semester_status_from_sgpa
from faculty.models import Designation, Faculty, FacultyCourseAssignment
from fees.models import Challan, FeeStructure
from students.models import Student


class ResultsPipelineIntegrationTests(TestCase):
    def setUp(self):
        AcademicPolicy.objects.get_or_create(defaults={'max_semester_credit_hours': 21})
        self.dept = Department.objects.create(department_code='RES', department_name='Results')
        self.program = DegreeProgram.objects.create(
            department=self.dept, program_name='BS Res', program_code='RES',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.semester = Semester.objects.create(
            semester_name='Res Fall', academic_year=2026, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=True,
        )
        self.course = Course.objects.create(
            department=self.dept, course_code='RES101', course_name='Res Course',
            credit_hours=3, course_type='core',
        )
        ProgramCourse.objects.create(program=self.program, course=self.course, semester_number=1, is_core=True)
        ProgramCourse.objects.create(
            program=self.program,
            course=Course.objects.create(
                department=self.dept, course_code='RES102', course_name='Res 2',
                credit_hours=3, course_type='core',
            ),
            semester_number=2, is_core=True,
        )
        admin = User.objects.create_user(email='res_admin@test.edu', username='res_admin', password='p', user_type='admin')
        teacher = User.objects.create_user(email='res_tea@test.edu', username='res_tea', password='p', user_type='teacher')
        des = Designation.objects.create(designation_title='Lec')
        self.faculty = Faculty.objects.create(
            user=teacher, department=self.dept, program=self.program, designation=des,
            employee_code='RES-F1', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        for pc in ProgramCourse.objects.filter(program=self.program):
            FacultyCourseAssignment.objects.create(faculty=self.faculty, program=self.program, course=pc.course)
            CourseOffering.objects.create(course=pc.course, semester=self.semester, faculty=self.faculty)
        FeeStructure.objects.create(
            program=self.program, semester_number=1, fee_type='semester_fee',
            amount=Decimal('50000'), effective_from=timezone.now().date(),
        )
        FeeStructure.objects.create(
            program=self.program, semester_number=2, fee_type='semester_fee',
            amount=Decimal('50000'), effective_from=timezone.now().date(),
        )
        user = User.objects.create_user(email='res_stu@test.edu', username='res_stu', password='p', user_type='student')
        self.student = Student.objects.create(
            user=user, program=self.program, registration_number='RES-001',
            batch_year=2026, admission_date=timezone.now().date(), current_semester=1,
        )
        self.admin = admin
        self.grade = Grade.objects.create(
            grade_letter='A', min_percentage=80, max_percentage=100,
            grade_points=Decimal('4.0'), status='pass',
        )

    def test_generate_results_from_final_grades(self):
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        offering = CourseOffering.objects.filter(course=self.course).first()
        reg = CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=offering,
            student=self.student, status='registered',
        )
        FinalGrade.objects.create(
            registration=reg, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=85, total_marks=100, percentage=85,
            grade=self.grade, status='pass',
        )
        stats = generate_results_for_semester(self.semester)
        self.assertEqual(stats['results_created_or_updated'], 1)
        sgpa = compute_student_sgpa(self.student, self.semester)
        self.assertGreater(float(sgpa['sgpa']), 0)

    def test_publish_result_then_promote_with_fee(self):
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester, status='completed')
        offering = CourseOffering.objects.filter(course=self.course).first()
        reg = CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=offering,
            student=self.student, status='completed',
        )
        FinalGrade.objects.create(
            registration=reg, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=90, total_marks=100, percentage=90,
            grade=self.grade, status='pass',
        )
        generate_results_for_semester(self.semester)
        result = Result.objects.get(student=self.student, semester=self.semester)
        result.is_published = True
        result.save()

        Challan.objects.create(
            challan_number='CH-RES-1', student=self.student, semester=self.semester,
            curriculum_semester=2,
            due_date=timezone.now().date(), total_amount=Decimal('50000'),
            amount_paid=Decimal('50000'),
            status='paid', generated_by=self.admin,
        )
        promo = promote_student_after_published_result(self.student, self.semester, self.admin)
        self.assertTrue(promo.get('promoted'), promo)
        self.student.refresh_from_db()
        self.assertEqual(self.student.current_semester, 2)

    def test_final_grade_uses_weighted_points_not_raw_marks(self):
        Grade.objects.create(
            grade_letter='C', min_percentage=50, max_percentage=59.99,
            grade_points=Decimal('2.0'), status='pass',
        )
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        offering = CourseOffering.objects.filter(course=self.course).first()
        reg = CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=offering,
            student=self.student, status='registered',
        )
        quiz_type = ExamType.objects.create(
            type_name='Quiz', weightage_percentage=10, marks_period='pre_mid',
        )
        mid_type = ExamType.objects.create(
            type_name='Mid Term', weightage_percentage=30, marks_period='mid_term',
        )
        final_type = ExamType.objects.create(
            type_name='Final Term', weightage_percentage=40, marks_period='final',
        )
        quiz = Examination.objects.create(
            course=self.course, semester=self.semester, offering=offering, exam_type=quiz_type,
            exam_name='Quiz 1', assessment_category='quiz', weight_percentage=10,
            total_marks=Decimal('10'), passing_marks=Decimal('4'),
        )
        mid = Examination.objects.create(
            course=self.course, semester=self.semester, offering=offering, exam_type=mid_type,
            exam_name='Mid Term', assessment_category='mid_term', weight_percentage=30,
            total_marks=Decimal('30'), passing_marks=Decimal('15'),
        )
        final = Examination.objects.create(
            course=self.course, semester=self.semester, offering=offering, exam_type=final_type,
            exam_name='Final Term', assessment_category='final', weight_percentage=40,
            total_marks=Decimal('40'), passing_marks=Decimal('20'),
        )
        Marks.objects.create(
            exam=quiz, student=self.student, registration=reg,
            obtained_marks=Decimal('5'), entered_by=self.faculty,
        )
        Marks.objects.create(
            exam=mid, student=self.student, registration=reg,
            obtained_marks=Decimal('15'), entered_by=self.faculty,
        )
        Marks.objects.create(
            exam=final, student=self.student, registration=reg,
            obtained_marks=Decimal('32'), entered_by=self.faculty,
        )

        compute_offering_final_grades(offering)

        fg = FinalGrade.objects.get(registration=reg)
        self.assertEqual(float(fg.total_obtained_marks), 52.0)
        self.assertEqual(float(fg.total_marks), 80.0)
        self.assertEqual(float(fg.percentage), 65.0)

    def test_one_fail_with_sgpa_above_threshold_is_pass_not_probation(self):
        """Failing one course does not trigger probation when SGPA meets the pass threshold."""
        fail_grade = Grade.objects.create(
            grade_letter='F', min_percentage=0, max_percentage=49.99,
            grade_points=Decimal('0.0'), status='fail',
        )
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        offering = CourseOffering.objects.filter(course=self.course).first()
        courses = [self.course] + list(
            Course.objects.filter(department=self.dept).exclude(course_id=self.course.course_id)[:3]
        )
        for course in courses:
            off = CourseOffering.objects.filter(course=course).first()
            if not off:
                off = CourseOffering.objects.create(
                    course=course, semester=self.semester, faculty=self.faculty,
                )
            reg = CourseRegistration.objects.create(
                enrollment=enrollment, course=course, offering=off,
                student=self.student, status='registered',
            )
            is_fail = course.course_id == self.course.course_id
            FinalGrade.objects.create(
                registration=reg, student=self.student, course=course, semester=self.semester,
                total_obtained_marks=23 if is_fail else 85, total_marks=100,
                percentage=23 if is_fail else 85,
                grade=fail_grade if is_fail else self.grade,
                status='fail' if is_fail else 'pass',
            )

        stats = compute_student_sgpa(self.student, self.semester)
        self.assertEqual(stats['fail_count'], 1)
        self.assertGreaterEqual(float(stats['sgpa']), 2.0)
        self.assertEqual(stats['status'], 'pass')
        self.assertEqual(
            semester_status_from_sgpa(stats['sgpa'], stats['fail_count']),
            'pass',
        )

    def test_cgpa_includes_failed_course_with_zero_points(self):
        fail_grade = Grade.objects.create(
            grade_letter='F', min_percentage=0, max_percentage=49.99,
            grade_points=Decimal('0.0'), status='fail',
        )
        enrollment = Enrollment.objects.create(student=self.student, semester=self.semester)
        offering = CourseOffering.objects.filter(course=self.course).first()
        reg = CourseRegistration.objects.create(
            enrollment=enrollment, course=self.course, offering=offering,
            student=self.student, status='registered',
        )
        FinalGrade.objects.create(
            registration=reg, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=30, total_marks=100, percentage=30,
            grade=fail_grade, status='fail',
        )
        cgpa = compute_student_cgpa(self.student)
        self.assertEqual(float(cgpa), 0.0)

    def test_cgpa_uses_best_attempt_when_course_repeated(self):
        fail_grade = Grade.objects.create(
            grade_letter='F', min_percentage=0, max_percentage=59.99,
            grade_points=Decimal('0.0'), status='fail',
        )
        sem2 = Semester.objects.create(
            semester_name='Res Spring', academic_year=2027, semester_type='spring',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=False,
        )
        offering2 = CourseOffering.objects.create(
            course=self.course, semester=sem2, faculty=self.faculty,
        )
        enrollment1 = Enrollment.objects.create(student=self.student, semester=self.semester)
        enrollment2 = Enrollment.objects.create(student=self.student, semester=sem2)
        offering = CourseOffering.objects.filter(course=self.course, semester=self.semester).first()
        reg_fail = CourseRegistration.objects.create(
            enrollment=enrollment1, course=self.course, offering=offering,
            student=self.student, status='registered', registration_type='regular',
        )
        FinalGrade.objects.create(
            registration=reg_fail, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=30, total_marks=100, percentage=30,
            grade=fail_grade, status='fail',
        )
        reg_repeat = CourseRegistration.objects.create(
            enrollment=enrollment2, course=self.course, offering=offering2,
            student=self.student, status='completed', registration_type='repeat',
        )
        FinalGrade.objects.create(
            registration=reg_repeat, student=self.student, course=self.course, semester=sem2,
            total_obtained_marks=85, total_marks=100, percentage=85,
            grade=self.grade, status='pass',
        )
        cgpa = compute_student_cgpa(self.student)
        self.assertEqual(float(cgpa), 4.0)

    def test_repeat_pass_refresh_updates_cgpa_on_submit(self):
        fail_grade = Grade.objects.create(
            grade_letter='F', min_percentage=0, max_percentage=59.99,
            grade_points=Decimal('0.0'), status='fail',
        )
        sem2 = Semester.objects.create(
            semester_name='Res Spring', academic_year=2027, semester_type='spring',
            start_date=timezone.now().date(), end_date=timezone.now().date(), is_current=False,
        )
        offering_repeat = CourseOffering.objects.create(
            course=self.course, semester=sem2, faculty=self.faculty, repeat_offering=True,
        )
        enrollment1 = Enrollment.objects.create(student=self.student, semester=self.semester)
        enrollment2 = Enrollment.objects.create(student=self.student, semester=sem2)
        offering = CourseOffering.objects.filter(course=self.course, semester=self.semester).first()
        reg_fail = CourseRegistration.objects.create(
            enrollment=enrollment1, course=self.course, offering=offering,
            student=self.student, status='completed', registration_type='regular',
        )
        FinalGrade.objects.create(
            registration=reg_fail, student=self.student, course=self.course, semester=self.semester,
            total_obtained_marks=30, total_marks=100, percentage=30,
            grade=fail_grade, status='fail',
        )
        Result.objects.create(
            student=self.student, semester=self.semester,
            sgpa=Decimal('0.00'), cgpa=Decimal('0.00'), status='fail', is_published=True,
        )
        reg_repeat = CourseRegistration.objects.create(
            enrollment=enrollment2, course=self.course, offering=offering_repeat,
            student=self.student, status='completed', registration_type='repeat',
        )
        FinalGrade.objects.create(
            registration=reg_repeat, student=self.student, course=self.course, semester=sem2,
            total_obtained_marks=85, total_marks=100, percentage=85,
            grade=self.grade, status='pass',
        )

        refresh_students_after_offering_grades(offering_repeat)

        self.student.refresh_from_db()
        self.assertEqual(float(self.student.cgpa), 4.0)
        sem1_result = Result.objects.get(student=self.student, semester=self.semester)
        self.assertEqual(float(sem1_result.cgpa), 4.0)
        sem2_result = Result.objects.get(student=self.student, semester=sem2)
        self.assertEqual(float(sem2_result.sgpa), 4.0)
