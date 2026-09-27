"""Attendance module API tests."""
from datetime import timedelta

from django.utils import timezone

from accounts.tests.base import Campus360APITestCase, make_user, grant_permissions
from academics.models import Department, DegreeProgram, Semester, Course, CourseOffering
from faculty.models import Designation, Faculty
from students.models import Student
from attendance.models import LeaveApplication


class AttendanceAPITests(Campus360APITestCase):
    def setUp(self):
        dept = Department.objects.create(department_code='ATT', department_name='Att')
        program = DegreeProgram.objects.create(
            department=dept, program_name='BS Att', program_code='ATT',
            degree_level='BS', duration_years=4, total_semesters=8, total_credit_hours=130,
        )
        self.student_user = make_user('att_stu@test.edu', 'att_stu', 'student')
        grant_permissions(self.student_user, ['attendance.view_own_attendance'], role_name='Student')
        self.student = Student.objects.create(
            user=self.student_user, program=program, registration_number='ATT-STU-1',
            batch_year=2025, current_semester=1, admission_date=timezone.now().date(),
        )
        self.teacher = make_user('att_tea@test.edu', 'att_tea', 'teacher')
        grant_permissions(self.teacher, [
            'attendance.mark_attendance', 'attendance.view_attendance',
        ], role_name='Teacher')
        des = Designation.objects.create(designation_title='Lecturer')
        faculty = Faculty.objects.create(
            user=self.teacher, department=dept, program=program, designation=des,
            employee_code='ATT-F1', qualification='MS', joining_date=timezone.now().date(),
            employment_type='permanent',
        )
        semester = Semester.objects.create(
            semester_name='Fall 2025', academic_year=2025, semester_type='fall',
            start_date=timezone.now().date(), end_date=timezone.now().date() + timedelta(days=120),
        )
        course = Course.objects.create(
            department=dept, course_code='ATT101', course_name='Attendance 101', credit_hours=3, course_type='core',
        )
        self.offering = CourseOffering.objects.create(
            course=course, semester=semester, faculty=faculty,
        )
        today = timezone.now().date()
        self.pending_leave = LeaveApplication.objects.create(
            student=self.student, offering=self.offering, reason='Medical',
            start_date=today + timedelta(days=1), end_date=today + timedelta(days=2), status='pending',
        )
        self.rejected_leave = LeaveApplication.objects.create(
            student=self.student, offering=self.offering, reason='Travel',
            start_date=today + timedelta(days=3), end_date=today + timedelta(days=4), status='rejected',
        )
        self.approved_leave = LeaveApplication.objects.create(
            student=self.student, offering=self.offering, reason='Family',
            start_date=today + timedelta(days=5), end_date=today + timedelta(days=6), status='approved',
        )

    def test_student_can_view_own_summary(self):
        self.auth_as(self.student_user)
        r = self.client.get('/api/attendance/summary/me/')
        self.assertIn(r.status_code, (200, 404))

    def test_teacher_can_list_attendance(self):
        self.auth_as(self.teacher)
        r = self.client.get('/api/attendance/')
        self.assertEqual(r.status_code, 200)

    def test_student_cannot_mark_attendance(self):
        self.auth_as(self.student_user)
        r = self.client.post('/api/attendance/mark/', {}, format='json')
        self.assertEqual(r.status_code, 403)

    def test_student_can_delete_pending_leave(self):
        self.auth_as(self.student_user)
        r = self.client.delete(f'/api/attendance/leaves/{self.pending_leave.leave_id}/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(LeaveApplication.objects.filter(leave_id=self.pending_leave.leave_id).exists())

    def test_student_can_delete_rejected_leave(self):
        self.auth_as(self.student_user)
        r = self.client.delete(f'/api/attendance/leaves/{self.rejected_leave.leave_id}/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(LeaveApplication.objects.filter(leave_id=self.rejected_leave.leave_id).exists())

    def test_student_cannot_delete_approved_leave(self):
        self.auth_as(self.student_user)
        r = self.client.delete(f'/api/attendance/leaves/{self.approved_leave.leave_id}/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Approved', r.data['error'])
        self.assertTrue(LeaveApplication.objects.filter(leave_id=self.approved_leave.leave_id).exists())
