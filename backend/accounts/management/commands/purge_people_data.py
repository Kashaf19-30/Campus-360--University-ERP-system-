"""
Remove all students, applicants, teachers/faculty, and their transactional data.
Preserves: admins, finance officers, curriculum, semesters, grades, exam types, RBAC.

  python manage.py purge_people_data --confirm
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Delete all students, applicants, faculty/teachers and related records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Required. Confirms destructive purge.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stderr.write(self.style.ERROR(
                'This permanently deletes students, applicants, and faculty data.\n'
                'Re-run with: python manage.py purge_people_data --confirm'
            ))
            return

        from accounts.models import User, UserRole, LoginSession, PasswordReset
        from admissions.models import (
            AdmissionApplication, Applicant, AcademicRecord,
            ProgramPreference, ApplicantDocument, AdmissionDecision, AdmissionLog,
        )
        from students.models import Student, StudentProfile
        from enrollments.models import Enrollment, CourseRegistration, RepeatCourseRequest
        from examinations.models import (
            Examination, Marks, FinalGrade, Result, ResultApproval,
            MarksEditPermission, OfferingMarksEditRequest,
        )
        from fees.models import Challan
        from attendance.models import Attendance, AttendanceRecord, StudentAttendanceSummary, LeaveApplication
        from faculty.models import Faculty, FacultyCourseAssignment, EmployeeProfile
        from academics.models import CourseOffering, Department
        from notifications.models import Notification
        from complaints.models import Complaint

        counts = {}

        def bump(label, n):
            counts[label] = counts.get(label, 0) + n

        # --- Academic / exam data tied to people ---
        bump('offering_marks_edit_requests', OfferingMarksEditRequest.objects.all().delete()[0])
        bump('marks_edit_permissions', MarksEditPermission.objects.all().delete()[0])
        bump('marks', Marks.objects.all().delete()[0])
        bump('final_grades', FinalGrade.objects.all().delete()[0])
        bump('result_approvals', ResultApproval.objects.all().delete()[0])
        bump('results', Result.objects.all().delete()[0])
        bump('repeat_requests', RepeatCourseRequest.objects.all().delete()[0])
        bump('attendance_records', AttendanceRecord.objects.all().delete()[0])
        bump('attendance_summaries', StudentAttendanceSummary.objects.all().delete()[0])
        bump('leave_applications', LeaveApplication.objects.all().delete()[0])
        bump('attendance_sessions', Attendance.objects.all().delete()[0])
        bump('course_registrations', CourseRegistration.objects.all().delete()[0])
        bump('enrollments', Enrollment.objects.all().delete()[0])
        bump('challans', Challan.objects.all().delete()[0])
        bump('examinations', Examination.objects.all().delete()[0])
        bump('course_offerings', CourseOffering.objects.all().delete()[0])
        bump('faculty_course_assignments', FacultyCourseAssignment.objects.all().delete()[0])

        faculty_ids = list(Faculty.objects.values_list('faculty_id', flat=True))
        bump('employee_profiles', EmployeeProfile.objects.filter(
            employee_type='faculty', employee_id__in=faculty_ids,
        ).delete()[0])

        bump('student_profiles', StudentProfile.objects.all().delete()[0])
        bump('students', Student.objects.all().delete()[0])

        bump('admission_logs', AdmissionLog.objects.all().delete()[0])
        bump('admission_decisions', AdmissionDecision.objects.all().delete()[0])
        bump('program_preferences', ProgramPreference.objects.all().delete()[0])
        bump('applicant_documents', ApplicantDocument.objects.all().delete()[0])
        bump('academic_records', AcademicRecord.objects.all().delete()[0])
        bump('admission_applications', AdmissionApplication.objects.all().delete()[0])
        bump('applicants', Applicant.objects.all().delete()[0])

        Department.objects.filter(hod__isnull=False).update(hod=None)
        bump('faculty', Faculty.objects.all().delete()[0])

        purge_types = ['student', 'teacher', 'applicant']
        users_qs = User.objects.filter(user_type__in=purge_types)
        user_ids = list(users_qs.values_list('user_id', flat=True))

        bump('complaints', Complaint.objects.filter(submitted_by_id__in=user_ids).delete()[0])
        bump('notifications', Notification.objects.filter(recipient_id__in=user_ids).delete()[0])
        bump('login_sessions', LoginSession.objects.filter(user_id__in=user_ids).delete()[0])
        bump('password_resets', PasswordReset.objects.filter(user_id__in=user_ids).delete()[0])
        bump('user_roles', UserRole.objects.filter(user_id__in=user_ids).delete()[0])
        bump('users', users_qs.delete()[0])

        self.stdout.write(self.style.SUCCESS('Purge complete. Preserved: admins, finance officers, curriculum, semesters.'))
        for label, n in sorted(counts.items()):
            if n:
                self.stdout.write(f'  {label}: {n}')

        self.stdout.write('')
        self.stdout.write('Remaining users:')
        for email, ut in User.objects.values_list('email', 'user_type'):
            self.stdout.write(f'  {email} ({ut})')
        self.stdout.write('')
        self.stdout.write('Next: python manage.py seed_erp_data')
