"""Delete the E2E walkthrough demo student and all related records."""
from django.core.management.base import BaseCommand
from django.db import transaction

WALKTHROUGH_EMAIL = 'walkthrough.student@campus360.edu'


class Command(BaseCommand):
    help = 'Remove walkthrough.student@campus360.edu and all linked academic/fee records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            default=WALKTHROUGH_EMAIL,
            help='Student user email to delete (default: walkthrough student)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from accounts.models import User
        from students.models import Student

        email = options['email']
        user = User.objects.filter(email=email).first()
        if not user:
            self.stdout.write(self.style.WARNING(f'No user with email {email}'))
            return

        student = Student.objects.filter(user=user).first()
        if student:
            reg = student.registration_number
            self._purge_student(student)
            self.stdout.write(self.style.SUCCESS(f'Deleted student {reg} and related records.'))
        else:
            self.stdout.write('No student record; cleaning applicant data only.')
            self._purge_applicant(user)

        user.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted user {email}'))

    def _purge_applicant(self, user):
        from admissions.models import (
            AdmissionApplication, Applicant, AcademicRecord,
            ProgramPreference, ApplicantDocument,
        )
        from complaints.models import Complaint

        Complaint.objects.filter(submitted_by=user).delete()
        applicant = Applicant.objects.filter(user=user).first()
        if not applicant:
            return
        for app in AdmissionApplication.objects.filter(applicant=applicant):
            ProgramPreference.objects.filter(application=app).delete()
            app.delete()
        ApplicantDocument.objects.filter(applicant=applicant).delete()
        AcademicRecord.objects.filter(applicant=applicant).delete()
        applicant.delete()

    def _purge_student(self, student):
        from enrollments.models import Enrollment, CourseRegistration, RepeatCourseRequest
        from examinations.models import Marks, FinalGrade, Result, ResultApproval, MarksEditPermission
        from fees.models import Challan
        from attendance.models import AttendanceRecord, StudentAttendanceSummary, LeaveApplication

        RepeatCourseRequest.objects.filter(student=student).delete()
        Marks.objects.filter(student=student).delete()
        FinalGrade.objects.filter(student=student).delete()
        for result in Result.objects.filter(student=student):
            ResultApproval.objects.filter(result=result).delete()
            result.delete()
        MarksEditPermission.objects.filter(student=student).delete()
        CourseRegistration.objects.filter(student=student).delete()
        Enrollment.objects.filter(student=student).delete()
        Challan.objects.filter(student=student).delete()
        AttendanceRecord.objects.filter(student=student).delete()
        StudentAttendanceSummary.objects.filter(student=student).delete()
        LeaveApplication.objects.filter(student=student).delete()
        user = student.user
        if hasattr(student, 'profile'):
            student.profile.delete()
        student.delete()
        self._purge_applicant(user)
