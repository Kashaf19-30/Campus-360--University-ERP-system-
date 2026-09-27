"""Notifications module API tests."""
from django.utils import timezone

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department, DegreeProgram, Semester, Course, CourseOffering
from faculty.models import Designation, Faculty
from enrollments.models import Enrollment, CourseRegistration
from students.models import Student


class NotificationsAPITests(Campus360APITestCase):
    def setUp(self):
        self.student = make_user('not_stu@test.edu', 'not_stu', 'student')
        grant_permissions(self.student, ['announcements.view_announcement'], role_name='Student')
        self.admin = make_user('not_admin@test.edu', 'not_admin', 'admin')
        grant_permissions(self.admin, [
            'system.admin_access', 'announcements.manage_announcement',
        ], role_name='Admin')

    def test_student_can_list_notifications(self):
        self.auth_as(self.student)
        r = self.client.get('/api/notifications/')
        self.assertEqual(r.status_code, 200)

    def test_student_can_list_announcements(self):
        self.auth_as(self.student)
        r = self.client.get('/api/notifications/announcements/')
        self.assertEqual(r.status_code, 200)

    def test_admin_can_create_announcement_type_endpoint_exists(self):
        self.auth_as(self.admin)
        r = self.client.get('/api/notifications/types/')
        self.assertEqual(r.status_code, 200)


class TeacherAnnouncementAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='CS', department_name='CS')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS CS', program_code='BSCS',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        semester = Semester.objects.create(
            semester_name='Fall 2025', academic_year=2025, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date(),
        )
        course = Course.objects.create(
            department=dept, course_code='CS101', course_name='Intro', credit_hours=3, course_type='core',
        )
        self.teacher = make_user('ann_teacher@test.edu', 'ann_teacher', 'teacher')
        grant_permissions(self.teacher, [
            'announcements.view_announcement', 'announcements.create_announcement',
        ])
        designation = Designation.objects.create(designation_title='Lecturer')
        faculty = Faculty.objects.create(
            user=self.teacher, department=dept, program=program, designation=designation,
            employee_code='ANN-FAC', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        self.offering = CourseOffering.objects.create(
            course=course, semester=semester, faculty=faculty, is_active=True, marks_locked=False,
        )
        course2 = Course.objects.create(
            department=dept, course_code='CS102', course_name='Advanced', credit_hours=3, course_type='core',
        )
        self.locked_offering = CourseOffering.objects.create(
            course=course2, semester=semester, faculty=faculty, is_active=True, marks_locked=True,
        )
        student_user = make_user('ann_stu@test.edu', 'ann_stu', 'student')
        grant_permissions(student_user, ['announcements.view_announcement'], role_name='Student2')
        self.student = Student.objects.create(
            user=student_user, program=program, registration_number='ANN-001',
            batch_year=2025, admission_date=timezone.now().date(), current_semester=1,
        )
        enrollment = Enrollment.objects.create(student=self.student, semester=semester)
        CourseRegistration.objects.create(
            enrollment=enrollment, course=course, offering=self.offering,
            student=self.student, status='registered',
        )

    def test_teacher_target_options_only_active_uncompleted_courses(self):
        self.auth_as(self.teacher)
        r = self.client.get('/api/notifications/announcements/target-options/')
        self.assertEqual(r.status_code, 200)
        values = [o['value'] for o in r.data]
        self.assertIn(f'offering_{self.offering.offering_id}', values)
        self.assertNotIn(f'offering_{self.locked_offering.offering_id}', values)

    def test_teacher_cannot_announce_without_course(self):
        self.auth_as(self.teacher)
        r = self.client.post('/api/notifications/announcements/create/', {
            'title': 'Test',
            'content': 'Hello',
            'announcement_type': 'academic',
            'target_audience_option': 'students',
        }, format='json')
        self.assertEqual(r.status_code, 400)

    def test_teacher_can_announce_to_own_course(self):
        self.auth_as(self.teacher)
        r = self.client.post('/api/notifications/announcements/create/', {
            'title': 'Class update',
            'content': 'Quiz moved to Friday',
            'announcement_type': 'academic',
            'target_audience_option': f'offering_{self.offering.offering_id}',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['target_audience'], 'course_offering')
