"""
Run a complete Campus360 demo walkthrough once (ORM-driven).

  python manage.py run_e2e_walkthrough
  python manage.py run_e2e_walkthrough --keep   # leave walkthrough student in DB
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from admissions.models import (
    AdmissionApplication, AdmissionDecision, Applicant, AcademicRecord, ProgramPreference,
)
from admissions.views import _register_approved_student
from academics.models import CourseOffering, DegreeProgram, ProgramCourse, Semester, Department
from enrollments.models import CourseRegistration, RepeatCourseRequest
from enrollments.promotion import (
    enroll_student_for_semester,
    promote_student_after_published_result,
    try_complete_pending_promotion,
)
from examinations.models import Examination, Marks, FinalGrade, Result, ResultApproval
from examinations.results_pipeline import ensure_semester_result, generate_results_for_semester
from examinations.views import _compute_offering_final_grades
from faculty.models import Faculty, FacultyCourseAssignment
from fees.models import Challan
from students.models import Student, StudentProfile


WALK_EMAIL = 'walkthrough.student@campus360.edu'


def _pass_obtained(exam) -> Decimal:
    total = exam.total_marks or Decimal('100')
    return (total * Decimal('0.85')).quantize(Decimal('0.01'))


def _fail_obtained(exam) -> Decimal:
    total = exam.total_marks or Decimal('100')
    return max(Decimal('1'), (total * Decimal('0.15')).quantize(Decimal('0.01')))


def _pay_curriculum_challan(student, semester, curriculum_semester, admin):
    challan = Challan.objects.filter(
        student=student,
        semester=semester,
        curriculum_semester=curriculum_semester,
    ).first()
    if not challan:
        enroll_student_for_semester(
            student, semester, admin, curriculum_semester=curriculum_semester,
        )
        challan = Challan.objects.filter(
            student=student,
            semester=semester,
            curriculum_semester=curriculum_semester,
        ).first()
    if challan and challan.status != 'paid':
        challan.amount_paid = challan.total_amount
        challan.status = 'paid'
        challan.save(update_fields=['amount_paid', 'status'])
    return challan


def _enter_offering_marks(student, offering, faculty, *, fail=False):
    count = 0
    reg = CourseRegistration.objects.filter(
        student=student, offering=offering, status='registered',
    ).first()
    if not reg:
        return 0
    for exam in Examination.objects.filter(offering=offering):
        obtained = _fail_obtained(exam) if fail else _pass_obtained(exam)
        Marks.objects.update_or_create(
            exam=exam,
            student=student,
            defaults={
                'registration': reg,
                'obtained_marks': obtained,
                'is_absent': False,
                'entered_by': faculty,
            },
        )
        count += 1
    _compute_offering_final_grades(offering)
    offering.marks_locked = True
    offering.save(update_fields=['marks_locked'])
    return count


def _delete_walkthrough_user():
    from enrollments.repeat_utils import sync_offering_enrolled_count

    user = User.objects.filter(email=WALK_EMAIL).first()
    if not user:
        return False
    student = Student.objects.filter(user=user).first()
    offering_ids = []
    if student:
        offering_ids = list(
            CourseRegistration.objects.filter(student=student).values_list('offering_id', flat=True)
        )
        Challan.objects.filter(student=student).delete()
    applicant = Applicant.objects.filter(user=user).first()
    if applicant:
        apps = AdmissionApplication.objects.filter(applicant=applicant)
        AdmissionDecision.objects.filter(application__in=apps).delete()
    user.delete()
    for offering_id in {oid for oid in offering_ids if oid}:
        offering = CourseOffering.objects.filter(pk=offering_id).first()
        if offering:
            sync_offering_enrolled_count(offering)
    return True


class Command(BaseCommand):
    help = (
        'Execute full admission → finance → teach → results → repeat → graduation walkthrough.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Keep walkthrough student data after run (default: delete).',
        )

    def handle(self, *args, **options):
        log = []
        step_no = [0]

        def step(title, detail=''):
            step_no[0] += 1
            msg = f'[{step_no[0]}] {title}'
            if detail:
                msg += f' — {detail}'
            log.append(msg)
            self.stdout.write(self.style.SUCCESS(msg))

        def warn(msg):
            log.append(f'WARN: {msg}')
            self.stdout.write(self.style.WARNING(f'WARN: {msg}'))

        if not options['keep']:
            if _delete_walkthrough_user():
                step('CLEANUP PREVIOUS', 'Removed prior walkthrough student')

        from enrollments.repeat_utils import maybe_deactivate_empty_offering
        from academics.models import CourseOffering as CO

        deactivated = 0
        for offering in CO.objects.filter(is_active=True, marks_locked=False):
            if maybe_deactivate_empty_offering(offering):
                deactivated += 1
        if deactivated:
            step('EMPTY OFFERINGS', f'deactivated {deactivated} abandoned cohort shells')

        admin = User.objects.filter(user_type='admin', is_active=True).first()
        if not admin:
            self.stderr.write('Missing admin user. Run seed_erp_data first.')
            return

        semester = Semester.objects.filter(is_current=True).first()
        program = DegreeProgram.objects.filter(program_code='BSCS', is_active=True).first()
        if not program:
            program = DegreeProgram.objects.filter(is_active=True).first()
        fcit_dept = Department.objects.filter(department_code='FCIT').first()
        if not semester or not program or not fcit_dept:
            self.stderr.write('Missing semester, program, or FCIT department. Run seed commands first.')
            return

        from accounts.models import Role, UserRole
        from faculty.models import Designation

        teacher_user, teacher_created = User.objects.get_or_create(
            email='teacher@campus360.edu',
            defaults={
                'username': 'walkthrough.teacher',
                'user_type': 'teacher',
                'is_active': True,
            },
        )
        if teacher_created:
            teacher_user.set_password('Teacher@123')
            teacher_user.save()
            role_obj, _ = Role.objects.get_or_create(role_name='Teacher')
            UserRole.objects.create(user=teacher_user, role=role_obj, assigned_by=admin)

        designation = Designation.objects.first()
        faculty, _ = Faculty.objects.get_or_create(
            user=teacher_user,
            defaults={
                'department': fcit_dept,
                'designation': designation or Designation.objects.create(designation_title='Lecturer'),
                'employee_code': 'WT-FAC-001',
                'qualification': 'PhD Computer Science',
                'specialization': 'Software Engineering',
                'joining_date': timezone.now().date(),
                'employment_type': 'permanent',
                'status': 'active',
            },
        )

        step('SETUP', f'session={semester.semester_name}, program={program.program_code}')

        assigned = 0
        for pc in ProgramCourse.objects.filter(program=program).select_related('course'):
            _, created = FacultyCourseAssignment.objects.get_or_create(
                program=program,
                course=pc.course,
                defaults={'faculty': faculty, 'is_active': True},
            )
            if created:
                assigned += 1
        step(
            'TEACHER ASSIGNMENTS',
            f'{assigned} new, {ProgramCourse.objects.filter(program=program).count()} total courses',
        )

        walk_user, user_created = User.objects.get_or_create(
            email=WALK_EMAIL,
            defaults={
                'username': 'walkthrough.student',
                'user_type': 'applicant',
                'is_active': True,
            },
        )
        if user_created:
            walk_user.set_password('Walk@12345')
            walk_user.save()

        applicant, _ = Applicant.objects.get_or_create(
            user=walk_user,
            defaults={
                'first_name': 'Walk',
                'last_name': 'Through',
                'father_name': 'Demo Father',
                'cnic': '3520212345671',
                'date_of_birth': timezone.now().date().replace(year=2005),
                'gender': 'male',
                'phone': '03001234567',
                'perm_address': 'Demo City',
            },
        )

        app = AdmissionApplication.objects.filter(applicant=applicant).exclude(
            status__in=['rejected'],
        ).first()
        if not app:
            app = AdmissionApplication.objects.create(
                applicant=applicant,
                program=program,
                application_number=f'APP-WT-{uuid.uuid4().hex[:6].upper()}',
                session_type='spring',
                session_year=timezone.now().year,
                status='challan_pending',
                challan_paid=False,
            )
            ProgramPreference.objects.get_or_create(
                application=app,
                program=program,
                defaults={'preference_order': 1},
            )
            AcademicRecord.objects.get_or_create(
                applicant=applicant,
                qualification_level='inter',
                defaults={
                    'authority': 'BISE',
                    'qualification': 'Intermediate',
                    'institute': 'Demo College',
                    'start_year': 2020,
                    'end_year': 2022,
                    'grading_system': 'marks',
                    'obtained': Decimal('850'),
                    'total': Decimal('1100'),
                },
            )
        app.challan_paid = True
        app.status = 'under_review'
        app.program = program
        app.save(update_fields=['challan_paid', 'status', 'program'])
        step('ADMISSION FEE', f'{app.application_number} paid -> under_review')

        student = Student.objects.filter(user=walk_user).first()
        if not student:
            app.status = 'approved'
            app.is_documents_verified = True
            app.save(update_fields=['status', 'is_documents_verified'])
            reg = _register_approved_student(app, admin)
            if reg.get('error'):
                warn(reg['error'])
                self._print_summary(log)
                return
            student = reg['student']

        _pay_curriculum_challan(student, semester, 1, admin)
        enroll_stats = enroll_student_for_semester(student, semester, admin, curriculum_semester=1)
        regs = list(
            CourseRegistration.objects.filter(
                student=student,
                status='registered',
                enrollment__semester=semester,
            ).select_related('course', 'offering')
        )
        step(
            'REGISTER + SEM 1 ENROLL',
            f'{student.registration_number}, courses={enroll_stats.get("enrolled_courses") or [r.course.course_code for r in regs]}',
        )
        if not regs:
            warn('No course registrations — cannot continue.')
            self._print_summary(log)
            return

        from examinations.assessment_setup import initialize_semester_assessments as init_assess
        init_assess(semester.semester_id, created_by=admin)

        fail_course = min(regs, key=lambda r: r.course.course_code).course
        marks_entered = 0
        for reg in regs:
            if reg.offering:
                marks_entered += _enter_offering_marks(
                    student, reg.offering, faculty,
                    fail=reg.course_id == fail_course.course_id,
                )
        fg_fail = FinalGrade.objects.filter(student=student, course=fail_course).first()
        step(
            'SEM 1 MARKS',
            f'{marks_entered} rows; {fail_course.course_code}={fg_fail.status if fg_fail else "?"}',
        )

        generate_results_for_semester(semester)
        result = ensure_semester_result(student, semester)
        ResultApproval.objects.get_or_create(
            result=result,
            defaults={'approved_by': admin, 'approval_date': timezone.now().date()},
        )
        _pay_curriculum_challan(student, semester, 2, admin)
        result.is_published = True
        result.published_date = timezone.now().date()
        result.published_by = admin
        result.save(update_fields=['is_published', 'published_date', 'published_by'])

        from academics.policy_utils import apply_standing_after_publish
        apply_standing_after_publish(student, result, performed_by=admin)
        promo = promote_student_after_published_result(student, semester, performed_by=admin)
        if promo.get('promotion_pending'):
            try_complete_pending_promotion(student, semester, 2, admin)
        student.refresh_from_db()
        step('SEM 1 PROMOTE', f'now sem {student.current_semester}, promo={promo.get("promoted", promo.get("reason"))}')

        if fg_fail and fg_fail.status == 'fail':
            _pay_curriculum_challan(student, semester, student.current_semester, admin)
            repeat_req, _ = RepeatCourseRequest.objects.get_or_create(
                student=student,
                semester=semester,
                course=fail_course,
                defaults={'status': 'pending'},
            )
            repeat_req.status = 'approved'
            repeat_req.reviewed_by = admin
            repeat_req.reviewed_at = timezone.now()
            repeat_req.save()
            from enrollments.repeat_utils import enroll_approved_repeat_request
            repeat_result = enroll_approved_repeat_request(repeat_req, performed_by=admin)
            repeat_count = CourseRegistration.objects.filter(
                student=student, course=fail_course, status='registered',
            ).count()
            step(
                'REPEAT APPROVED',
                f'{fail_course.course_code}, active regs={repeat_count}, '
                f'warnings={repeat_result.get("warnings") or []}',
            )
            repeat_reg = CourseRegistration.objects.filter(
                student=student,
                course=fail_course,
                status='registered',
                registration_type='repeat',
            ).select_related('offering').first()
            if repeat_reg and repeat_reg.offering:
                _enter_offering_marks(student, repeat_reg.offering, faculty, fail=False)
                ensure_semester_result(student, semester)
                step('REPEAT MARKS PASSED', fail_course.course_code)
        else:
            warn(f'No fail grade on {fail_course.course_code} — repeat branch skipped.')

        total_semesters = program.total_semesters or 8
        while student.status != 'graduated' and student.current_semester <= total_semesters:
            student.refresh_from_db()
            cur = student.current_semester
            _pay_curriculum_challan(student, semester, cur, admin)
            enroll_student_for_semester(student, semester, admin, curriculum_semester=cur)
            cur_regs = list(
                CourseRegistration.objects.filter(
                    student=student,
                    status='registered',
                    enrollment__semester=semester,
                ).select_related('course', 'offering')
            )
            if not cur_regs:
                if cur >= total_semesters:
                    break
                warn(f'Sem {cur}: no registered courses to grade.')
                break

            init_assess(semester.semester_id, created_by=admin)
            for reg in cur_regs:
                if reg.offering and reg.offering.marks_locked:
                    reg.offering.marks_locked = False
                    reg.offering.save(update_fields=['marks_locked'])
                if reg.offering:
                    _enter_offering_marks(student, reg.offering, faculty, fail=False)

            ensure_semester_result(student, semester)
            next_sem = cur + 1
            if next_sem <= total_semesters:
                _pay_curriculum_challan(student, semester, next_sem, admin)

            result = Result.objects.get(student=student, semester=semester)
            if not result.is_published:
                result.is_published = True
                result.published_date = timezone.now().date()
                result.published_by = admin
                result.save(update_fields=['is_published', 'published_date', 'published_by'])
                apply_standing_after_publish(student, result, performed_by=admin)

            promo = promote_student_after_published_result(student, semester, performed_by=admin)
            if promo.get('promotion_pending') and promo.get('pending_promotion_semester'):
                try_complete_pending_promotion(
                    student, semester, promo['pending_promotion_semester'], admin,
                )
            student.refresh_from_db()

            if promo.get('graduated') or student.status == 'graduated':
                step('GRADUATION', student.registration_number)
                break
            if promo.get('graduation_blocked'):
                warn(f'Graduation blocked: {promo.get("reason")}')
                break
            if not promo.get('promoted') and not promo.get('graduated'):
                if student.current_semester >= total_semesters:
                    from students.degree_audit import run_degree_audit
                    audit = run_degree_audit(student)
                    if audit.get('eligible'):
                        student.status = 'graduated'
                        student.graduation_date = timezone.now().date()
                        student.save(update_fields=['status', 'graduation_date'])
                        step('GRADUATION', f'{student.registration_number} (degree audit)')
                    else:
                        warn(f'Final semester but not eligible: {audit.get("issues")}')
                    break
                warn(f'Sem {cur} promotion stalled: {promo.get("reason")}')
                break
            step(f'SEM {cur} DONE', f'now sem {student.current_semester}')

        profile, _ = StudentProfile.objects.get_or_create(student=student)
        profile.profile_locked = True
        profile.save(update_fields=['profile_locked'])
        step('PROFILE LOCK', f'status={student.status}, sem={student.current_semester}')

        if not options['keep']:
            _delete_walkthrough_user()
            step('CLEANUP', 'Walkthrough student removed')

        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('=== WALKTHROUGH COMPLETE ==='))
        if options['keep']:
            self.stdout.write(f'Login: {WALK_EMAIL} / Walk@12345')
        self._print_summary(log)

    def _print_summary(self, log):
        self.stdout.write('')
        for line in log:
            self.stdout.write(f'  {line}')
