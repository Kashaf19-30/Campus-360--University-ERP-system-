"""Re-enroll students whose fee challan is paid but curriculum courses were never registered."""
from django.core.management.base import BaseCommand

from academics.models import Semester, ProgramCourse
from fees.models import Challan
from enrollments.models import CourseRegistration
from enrollments.promotion import enroll_student_for_semester
from enrollments.progress_utils import is_regular_course_for_student
from accounts.models import User


class Command(BaseCommand):
    help = 'Register curriculum courses for paid challans that did not trigger enrollment.'

    def handle(self, *args, **options):
        session = Semester.objects.filter(is_current=True).first()
        if not session:
            self.stderr.write('No active session configured.')
            return

        admin = User.objects.filter(user_type='admin', is_active=True).first()
        if not admin:
            admin = User.objects.filter(is_superuser=True).first()

        fixed = 0
        for challan in Challan.objects.filter(status='paid').select_related('student', 'student__program'):
            sem_num = challan.curriculum_semester
            student = challan.student
            missing = []
            for pc in ProgramCourse.objects.filter(
                program=student.program, semester_number=sem_num,
            ).select_related('course'):
                has_reg = CourseRegistration.objects.filter(
                    student=student,
                    course=pc.course,
                    status='registered',
                    enrollment__semester=session,
                ).exists()
                if not has_reg and is_regular_course_for_student(student, pc.course, sem_num):
                    missing.append(pc.course.course_code)
            if not missing:
                continue
            stats = enroll_student_for_semester(
                student, session, performed_by=admin, curriculum_semester=sem_num,
            )
            enrolled = stats.get('enrolled_courses') or []
            if enrolled:
                fixed += 1
                self.stdout.write(
                    f'{student.registration_number} Semester {sem_num}: {", ".join(enrolled)}'
                )

        self.stdout.write(self.style.SUCCESS(f'Reconciled {fixed} student(s).'))
