"""
Extended E2E audit: admission -> enrollment -> marks -> promotion -> repeat -> graduation.
Run: python scripts/full_e2e_audit.py
"""
import os
import sys
import uuid
import traceback
from decimal import Decimal

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from accounts.rbac import ensure_user_role_for_type
from admissions.models import (
    AcademicRecord,
    AdmissionApplication,
    AdmissionDecision,
    Applicant,
    ApplicantDocument,
    ProgramPreference,
)
from admissions.views import _register_approved_student
from academics.models import CourseOffering, DegreeProgram, ProgramCourse, Semester
from enrollments.models import CourseRegistration, Enrollment, RepeatCourseRequest
from enrollments.promotion import (
    enroll_student_for_semester,
    promote_student_after_published_result,
)
from examinations.models import Examination, FinalGrade, Marks, Result, ResultApproval
from examinations.results_pipeline import generate_results_for_semester
from examinations.views import _compute_offering_final_grades
from faculty.models import Faculty, FacultyCourseAssignment
from fees.models import Challan
from students.degree_audit import run_degree_audit
from students.models import Student
from students.views import confirm_graduation  # noqa - use logic inline

E2E_EMAIL = 'e2e.audit@campus360.edu'
ISSUES = []
STEPS = []


def issue(severity, area, message, detail=''):
    ISSUES.append({'severity': severity, 'area': area, 'message': message, 'detail': detail})
    print(f'[{severity}] {area}: {message}' + (f' — {detail}' if detail else ''))


def step(n, title, detail=''):
    line = f'[{n}] {title}' + (f' — {detail}' if detail else '')
    STEPS.append(line)
    print('OK', line)


def delete_e2e_user():
    user = User.objects.filter(email=E2E_EMAIL).first()
    if not user:
        return
    from enrollments.repeat_utils import sync_offering_enrolled_count
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
    for oid in {x for x in offering_ids if x}:
        off = CourseOffering.objects.filter(pk=oid).first()
        if off:
            sync_offering_enrolled_count(off)


def pay_semester_challan(student, semester, curriculum_semester=None):
    sem_num = curriculum_semester or student.current_semester
    challan = Challan.objects.filter(
        student=student, semester=semester, curriculum_semester=sem_num,
    ).first()
    if not challan:
        enroll_student_for_semester(student, semester, curriculum_semester=sem_num)
        challan = Challan.objects.filter(
            student=student, semester=semester, curriculum_semester=sem_num,
        ).first()
    if challan and challan.status != 'paid':
        challan.status = 'paid'
        challan.amount_paid = challan.total_amount
        challan.save(update_fields=['status', 'amount_paid'])
    return challan


def complete_promotion_after_fee(student, semester, admin):
    """Pay target-semester fee and finish any pending promotion."""
    from enrollments.promotion import try_complete_pending_promotion

    result = Result.objects.filter(
        student=student, semester=semester, is_published=True, promotion_pending=True,
    ).order_by('-result_id').first()
    if result and result.pending_promotion_semester:
        pay_semester_challan(student, semester, result.pending_promotion_semester)
        promo = try_complete_pending_promotion(
            student, semester, result.pending_promotion_semester, admin,
        )
        student.refresh_from_db()
        return promo
    return None


def enter_passing_marks(student, regs, faculty, *, fail_course_id=None):
    count = 0
    for reg in regs:
        if not reg.offering:
            continue
        exams = Examination.objects.filter(offering=reg.offering)
        passing = reg.course_id != fail_course_id
        for exam in exams:
            obtained = Decimal('85') if passing else Decimal('20')
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
        _compute_offering_final_grades(reg.offering)
        reg.offering.marks_locked = True
        reg.offering.save(update_fields=['marks_locked'])
    return count


def publish_and_promote(student, semester, admin):
    generate_results_for_semester(semester)
    result = Result.objects.filter(student=student, semester=semester).first()
    if not result:
        return None, {'error': 'no result generated'}
    ResultApproval.objects.get_or_create(
        result=result,
        defaults={'approved_by': admin, 'approval_date': timezone.now().date()},
    )
    result.is_published = True
    result.published_date = timezone.now().date()
    result.published_by = admin
    result.save(update_fields=['is_published', 'published_date', 'published_by'])
    from academics.policy_utils import apply_standing_after_publish
    apply_standing_after_publish(student, result, performed_by=admin)
    promo = promote_student_after_published_result(student, semester, performed_by=admin)
    student.refresh_from_db()
    return result, promo


def run_audit():
    delete_e2e_user()

    admin = User.objects.filter(user_type='admin', is_active=True).first()
    semester = Semester.objects.filter(is_current=True).first()
    program = DegreeProgram.objects.filter(program_code='BSCS', is_active=True).first()
    faculty = Faculty.objects.filter(status='active').select_related('user').first()
    if not all([admin, semester, program, faculty]):
        issue('CRITICAL', 'SETUP', 'Missing admin, semester, program, or faculty')
        return

    # Ensure teacher assignments
    for pc in ProgramCourse.objects.filter(program=program).select_related('course'):
        FacultyCourseAssignment.objects.get_or_create(
            program=program, course=pc.course,
            defaults={'faculty': faculty, 'is_active': True},
        )

    # --- Admission ---
    user = User.objects.create_user(
        email=E2E_EMAIL, username='e2e.audit', password='E2e@Audit123', user_type='applicant',
    )
    applicant = Applicant.objects.create(
        user=user, first_name='E2E', last_name='Audit', cnic='3520212345999',
        date_of_birth=timezone.now().date().replace(year=2005), gender='male', phone='03009998877',
        perm_address='Audit Campus',
    )
    AcademicRecord.objects.create(
        applicant=applicant, qualification_level='inter', authority='BISE',
        qualification='Intermediate', institute='Demo', start_year=2020, end_year=2022,
        grading_system='marks', obtained=Decimal('900'), total=Decimal('1100'),
    )
    for doc_type in ('cnic_front', 'cnic_back', 'domicile', 'photograph', 'matric_marksheet', 'inter_marksheet'):
        ApplicantDocument.objects.create(
            applicant=applicant, document_type=doc_type, file_name=f'{doc_type}.pdf',
            file_path='seed/test-document.pdf', file_size=100, file_type='application/pdf',
            is_verified=True, verified_at=timezone.now(),
        )
    app = AdmissionApplication.objects.create(
        applicant=applicant, program=program,
        application_number=f'APP-E2E-{uuid.uuid4().hex[:6].upper()}',
        session_type='spring', session_year=timezone.now().year,
        status='under_review', challan_paid=True, is_documents_verified=True,
    )
    ProgramPreference.objects.create(application=app, program=program, preference_order=1)
    app.status = 'approved'
    app.save(update_fields=['status'])
    reg = _register_approved_student(app, admin)
    if reg.get('error'):
        issue('CRITICAL', 'ADMISSION', 'Register failed', reg['error'])
        return
    student = reg['student']
    step(1, 'ADMISSION', student.registration_number)

    if reg['enroll_result'].get('registration_blocked'):
        issue('HIGH', 'ADMISSION', 'Registration blocked without semester fee on approve',
              str(reg['enroll_result'].get('warnings')))

    pay_semester_challan(student, semester, 1)
    enroll_stats = enroll_student_for_semester(student, semester, admin)
    regs = list(
        CourseRegistration.objects.filter(student=student, status='registered').select_related('course', 'offering')
    )
    if not regs:
        issue('CRITICAL', 'ENROLLMENT', 'No courses after fee paid', str(enroll_stats))
        return
    step(2, 'ENROLLMENT SEM 1', f'{len(regs)} courses')

    from examinations.assessment_setup import initialize_semester_assessments
    initialize_semester_assessments(semester.semester_id, created_by=admin)

    fail_course = regs[0].course
    enter_passing_marks(student, regs, faculty, fail_course_id=fail_course.course_id)
    result, promo = publish_and_promote(student, semester, admin)
    if not result:
        issue('CRITICAL', 'RESULTS', 'No result after sem 1')
        return
    if promo.get('promotion_pending'):
        promo2 = complete_promotion_after_fee(student, semester, admin)
        if promo2:
            promo = promo2
        student.refresh_from_db()
    step(3, 'RESULTS + PROMOTE SEM 1', f'sem={student.current_semester}, promo={promo}')

    # Repeat request for failed course
    fg_fail = FinalGrade.objects.filter(student=student, course=fail_course, status='fail').exists()
    if fg_fail:
        pay_semester_challan(student, semester, student.current_semester)
        rr = RepeatCourseRequest.objects.create(
            student=student, semester=semester, course=fail_course, status='approved',
            reviewed_by=admin, reviewed_at=timezone.now(),
        )
        enroll_student_for_semester(student, semester, admin)
        repeat_reg = CourseRegistration.objects.filter(
            student=student, course=fail_course, status='registered',
        ).exists()
        if not repeat_reg:
            issue('HIGH', 'REPEAT', f'Repeat approved but not enrolled for {fail_course.course_code}')
        else:
            step(4, 'REPEAT REQUEST', fail_course.course_code)
    else:
        fg = FinalGrade.objects.filter(student=student, course=fail_course).first()
        issue('MEDIUM', 'REPEAT', 'Expected one failed course for repeat test',
              f'{fail_course.course_code} grade={fg.status if fg else "missing"}')

    # Fast-forward remaining semesters (pass all)
    total_semesters = program.total_semesters
    while student.current_semester <= total_semesters and student.status != 'graduated':
        cur = student.current_semester
        pay_semester_challan(student, semester, cur)
        enroll_stats = enroll_student_for_semester(student, semester, admin, curriculum_semester=cur)
        regs = list(
            CourseRegistration.objects.filter(
                student=student, status='registered', enrollment__semester=semester,
            ).select_related('course', 'offering')
        )
        if not regs and cur < total_semesters:
            issue('HIGH', 'ENROLLMENT', f'No courses enrolled at sem {cur}', str(enroll_stats))
            break
        if regs:
            initialize_semester_assessments(semester.semester_id, created_by=admin)
            enter_passing_marks(student, regs, faculty)
        result, promo = publish_and_promote(student, semester, admin)
        if promo.get('promotion_pending'):
            complete_promotion_after_fee(student, semester, admin)
            student.refresh_from_db()
        else:
            student.refresh_from_db()
        if promo.get('graduated') or student.status == 'graduated':
            step(5, 'GRADUATION VIA PROMOTION', student.registration_number)
            break
        if promo.get('graduation_blocked'):
            audit = run_degree_audit(student)
            issue('HIGH', 'GRADUATION', 'Blocked at final semester', str(audit.get('issues')))
            break
        step(4 + cur, f'SEM {cur} COMPLETE', f'now sem {student.current_semester}')

    audit = run_degree_audit(student)
    if student.current_semester > total_semesters and student.status != 'graduated':
        if audit.get('eligible'):
            student.status = 'graduated'
            student.graduation_date = timezone.now().date()
            student.save(update_fields=['status', 'graduation_date'])
            step(99, 'MANUAL GRADUATION', 'degree audit passed')
        else:
            issue('HIGH', 'GRADUATION', 'Final semester but not eligible', str(audit.get('issues')))

    # API smoke via test client
    try:
        from django.test import Client
        from accounts.utils import generate_jwt_token
        from accounts.models import LoginSession
        from datetime import timedelta

        client = Client()
        token = f'e2e-smoke-{user.user_id}'
        LoginSession.objects.update_or_create(
            user=user, session_token=token,
            defaults={'expires_at': timezone.now() + timedelta(days=1), 'is_active': True},
        )
        jwt = generate_jwt_token(user, token)
        endpoints = [
            '/api/students/me/',
            '/api/enrollments/me/',
            '/api/examinations/final-grades/me/',
            '/api/examinations/results/me/',
            '/api/students/me/degree-audit/',
            '/api/students/me/transcript/',
        ]
        for path in endpoints:
            resp = client.get(path, HTTP_AUTHORIZATION=f'Bearer {jwt}', HTTP_HOST='localhost')
            if resp.status_code >= 500:
                issue('CRITICAL', 'API', f'{path} returned {resp.status_code}', resp.content[:200].decode())
            elif resp.status_code >= 400:
                issue('MEDIUM', 'API', f'{path} returned {resp.status_code}', resp.content[:200].decode())
        step(100, 'STUDENT API CHECKS', f'{len(endpoints)} endpoints')
    except Exception as exc:
        issue('HIGH', 'API', 'Student API smoke failed', traceback.format_exc())

    delete_e2e_user()
    step(101, 'CLEANUP', 'E2E data deleted')


if __name__ == '__main__':
    try:
        run_audit()
    except Exception as exc:
        issue('CRITICAL', 'AUDIT', 'Unhandled exception', traceback.format_exc())
        delete_e2e_user()

    print('\n=== SUMMARY ===')
    print(f'Steps completed: {len(STEPS)}')
    print(f'Issues found: {len(ISSUES)}')
    for i in ISSUES:
        print(f"  [{i['severity']}] {i['area']}: {i['message']}")
        if i.get('detail'):
            print(f"    {i['detail'][:300]}")
