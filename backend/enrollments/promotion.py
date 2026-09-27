"""
Auto-enrollment: students are enrolled by the system after results are published.
No self-service course registration.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from academics.models import ProgramCourse, Semester
from academics.policy_utils import get_academic_policy
from academics.prerequisite_utils import (
    check_course_prerequisites,
    get_unmet_direct_prerequisite_courses,
)
from enrollments.models import Enrollment, CourseRegistration, RepeatCourseRequest
from examinations.models import FinalGrade
from fees.models import FeeStructure, Challan
from notifications.models import Notification, NotificationType
from academics.session_utils import curriculum_semester_for_course
from faculty.assignment_utils import pick_offering_for_student


def _can_enroll_in_course(student, course) -> tuple[bool, list]:
    ok, missing = check_course_prerequisites(student, course)
    return ok, missing


def _semester_fee_paid(student, semester, curriculum_semester=None) -> bool:
    sem_num = curriculum_semester if curriculum_semester is not None else student.current_semester
    challan = Challan.objects.filter(
        student=student,
        semester=semester,
        curriculum_semester=sem_num,
    ).first()
    return bool(challan and challan.status == 'paid')


def _failed_course_ids(student, semester) -> set:
    return set(
        FinalGrade.objects.filter(
            student=student, semester=semester, status='fail',
        ).values_list('course_id', flat=True)
    )


def _all_failed_course_ids(student) -> set:
    from enrollments.repeat_utils import passed_course_ids
    passed = passed_course_ids(student)
    return set(
        FinalGrade.objects.filter(student=student, status='fail')
        .exclude(course_id__in=passed)
        .values_list('course_id', flat=True)
    )


def _all_registered_credit_hours(enrollment) -> int:
    """All active semester registrations (regular + repeat)."""
    if not enrollment:
        return 0
    total = CourseRegistration.objects.filter(
        enrollment=enrollment, status='registered',
    ).aggregate(total=Sum('course__credit_hours'))['total']
    return total or 0


def _registered_credit_hours(enrollment) -> int:
    if not enrollment:
        return 0
    from enrollments.progress_utils import is_active_regular_registration
    regs = CourseRegistration.objects.filter(
        enrollment=enrollment, status='registered',
    ).select_related('course', 'student', 'student__program')
    return sum(r.course.credit_hours for r in regs if is_active_regular_registration(r))


def get_student_semester_credit_summary(student, semester) -> dict:
    """Current registered CH vs semester cap (for admin repeat review)."""
    policy = get_academic_policy()
    enrollment = Enrollment.objects.filter(student=student, semester=semester).first()
    enrolled_ch = _all_registered_credit_hours(enrollment)
    max_ch = policy.max_semester_credit_hours
    return {
        'enrolled_credit_hours': enrolled_ch,
        'max_semester_credit_hours': max_ch,
        'remaining_credit_hours': max(0, max_ch - enrolled_ch),
    }


def _can_add_course(enrollment, course, policy) -> bool:
    return _all_registered_credit_hours(enrollment) + course.credit_hours <= policy.max_semester_credit_hours


def _register_course(enrollment, student, course, offering, registration_type='regular') -> None:
    from enrollments.repeat_utils import prepare_offering_for_new_registration, sync_offering_enrolled_count

    if not _can_add_course(enrollment, course, get_academic_policy()):
        raise ValueError(f'Credit cap exceeded — cannot register {course.course_code}.')
    prepare_offering_for_new_registration(offering, registration_type)
    CourseRegistration.objects.create(
        enrollment=enrollment,
        course=course,
        offering=offering,
        student=student,
        registration_type=registration_type,
    )
    sync_offering_enrolled_count(offering)


def _curriculum_credit_hours(program, semester_number) -> int:
    return sum(
        pc.course.credit_hours for pc in ProgramCourse.objects.filter(
            program=program, semester_number=semester_number,
        ).select_related('course')
    )


def _enroll_curriculum_regular(
    student, enrollment, course, target_semester, program, policy, warnings, enrolled, blocked,
    *, curriculum_credit_total, notified_warnings,
) -> bool:
    """
    Phase 1: Register all current-semester curriculum courses as regular.
    Soft prerequisite = warning only. Curriculum is never skipped when total curriculum CH fits cap.
    """
    if CourseRegistration.objects.filter(enrollment=enrollment, course=course).exists():
        return False

    allowed, missing = _can_enroll_in_course(student, course)

    if not policy.soft_prerequisite_enrollment and not allowed:
        _append_blocked(blocked, course.course_code, '; '.join(missing))
        warnings.append(f'{course.course_code} deferred — prerequisites not met: {"; ".join(missing)}')
        return False

    if not _can_add_course(enrollment, course, policy):
        if curriculum_credit_total <= policy.max_semester_credit_hours:
            warnings.append(
                f'{course.course_code} could not fit — repeats may be using cap. '
                f'Curriculum total is {curriculum_credit_total} CH.'
            )
        _append_blocked(blocked, course.course_code, f'Semester credit limit ({policy.max_semester_credit_hours} CH) reached.')
        warnings.append(f'{course.course_code} deferred — credit hour limit reached.')
        return False

    offering = pick_offering_for_student(
        course, program, target_semester, student, warnings,
        curriculum_semester=curriculum_semester_for_course(program, course),
    )
    if not offering:
        return False

    _register_course(enrollment, student, course, offering, registration_type='regular')
    enrolled.append(course.course_code)

    if not allowed and policy.soft_prerequisite_enrollment:
        warnings.append(
            f'{course.course_code} enrolled — complete prerequisite(s): {"; ".join(missing)}'
        )
        if course.course_code not in notified_warnings:
            from notifications.system_notify import notify_user
            notify_user(
                student.user,
                'Registration',
                f'Prerequisite reminder — {course.course_code}',
                f'You are enrolled in {course.course_code}. Please complete: {"; ".join(missing)}.',
                priority='normal',
            )
            notified_warnings.add(course.course_code)
    return True


def _enroll_auto_prerequisite_repeats(
    student, enrollment, program_courses, target_semester, program, policy,
    warnings, enrolled, all_failed_ids,
) -> None:
    """Phase 2: Optional repeat of failed prerequisites — skipped first if cap is tight."""
    seen_prereqs = set()
    for pc in program_courses:
        for prereq in get_unmet_direct_prerequisite_courses(student, pc.course):
            if prereq.course_id in seen_prereqs:
                continue
            seen_prereqs.add(prereq.course_id)
            if prereq.course_id not in all_failed_ids:
                continue
            if CourseRegistration.objects.filter(enrollment=enrollment, course=prereq).exists():
                continue
            if not policy.auto_enroll_failed_prerequisites:
                continue
            if not _can_add_course(enrollment, prereq, policy):
                warnings.append(
                    f'{prereq.course_code} (prerequisite repeat) skipped — '
                    f'no credit hours left after curriculum ({policy.max_semester_credit_hours} CH cap).'
                )
                continue
            offering = pick_offering_for_student(
                prereq, program, target_semester, student, warnings,
                repeat_offering=True,
            )
            if not offering:
                continue
            _register_course(
                enrollment, student, prereq, offering, registration_type='prerequisite_repeat',
            )
            enrolled.append(f'{prereq.course_code} (prerequisite repeat)')
            warnings.append(f'{prereq.course_code} auto-enrolled as prerequisite repeat.')


def _append_blocked(blocked, course_code, reason):
    if not any(b['course_code'] == course_code for b in blocked):
        blocked.append({'course_code': course_code, 'reason': reason})


def enroll_student_for_semester(student, target_semester, performed_by=None, curriculum_semester=None) -> dict:
    """
    Enroll student in curriculum courses for their current_semester number
    (or curriculum_semester when promoting before persisting the bump).
    """
    from students.models import Student

    if isinstance(student, int):
        student = Student.objects.select_related('program').get(student_id=student)

    sem_num = curriculum_semester if curriculum_semester is not None else student.current_semester
    program = student.program
    performed_by = performed_by or student.user
    policy = get_academic_policy()
    all_failed_ids = _all_failed_course_ids(student)

    enrollment, _ = Enrollment.objects.get_or_create(
        student=student,
        semester=target_semester,
        defaults={'status': 'enrolled'},
    )

    if not _semester_fee_paid(student, target_semester, sem_num):
        _ensure_semester_challan(student, program, target_semester, sem_num, performed_by)
        return {
            'enrolled_courses': [],
            'warnings': ['Registration blocked — outstanding semester fee. Contact the Finance Office.'],
            'blocked_courses': [],
            'registration_blocked': True,
        }

    if enrollment.status != 'enrolled':
        enrollment.status = 'enrolled'
        enrollment.save(update_fields=['status'])

    enrolled = []
    warnings = []
    blocked = []
    notified_warnings = set()

    program_courses = list(ProgramCourse.objects.filter(
        program=program, semester_number=sem_num,
    ).select_related('course'))
    curriculum_ch = _curriculum_credit_hours(program, sem_num)

    # Phase 1: all regular curriculum courses first (seeded sem load ≤ cap — no skipping)
    for pc in program_courses:
        _enroll_curriculum_regular(
            student, enrollment, pc.course, target_semester, program, policy,
            warnings, enrolled, blocked,
            curriculum_credit_total=curriculum_ch,
            notified_warnings=notified_warnings,
        )

    # Phase 2: failed prerequisite repeats only if cap still allows (repeat skipped, not curriculum)
    _enroll_auto_prerequisite_repeats(
        student, enrollment, program_courses, target_semester, program, policy,
        warnings, enrolled, all_failed_ids,
    )

    # Phase 3: admin-approved repeats
    approved_repeats = RepeatCourseRequest.objects.filter(
        student=student, semester=target_semester, status='approved',
    ).select_related('course')
    for repeat_req in approved_repeats:
        if CourseRegistration.objects.filter(enrollment=enrollment, course=repeat_req.course).exists():
            continue
        allowed, missing = _can_enroll_in_course(student, repeat_req.course)
        if not allowed:
            _append_blocked(blocked, repeat_req.course.course_code, '; '.join(missing))
            warnings.append(f'Repeat {repeat_req.course.course_code} blocked — {"; ".join(missing)}')
            continue
        if not _can_add_course(enrollment, repeat_req.course, policy):
            warnings.append(f'Repeat {repeat_req.course.course_code} skipped — credit hour limit reached.')
            continue
        offering = pick_offering_for_student(
            repeat_req.course, program, target_semester, student, warnings,
            repeat_offering=True,
        )
        if not offering:
            continue
        _register_course(
            enrollment, student, repeat_req.course, offering, registration_type='repeat',
        )
        enrolled.append(f'{repeat_req.course.course_code} (repeat)')

    enrollment.total_credit_hours_registered = _all_registered_credit_hours(enrollment)
    enrollment.save(update_fields=['total_credit_hours_registered'])

    _ensure_semester_challan(student, program, target_semester, sem_num, performed_by)

    notif_type, _ = NotificationType.objects.get_or_create(
        type_name='Academic', defaults={'description': 'Academic updates'},
    )
    course_list = ', '.join(enrolled) if enrolled else 'pending course assignment'
    deferred = ', '.join(b['course_code'] for b in blocked) if blocked else 'none'
    Notification.objects.create(
        notification_type=notif_type,
        recipient=student.user,
        title=f'Enrolled — Semester {sem_num}',
        message=f'Semester {sem_num} registration: {course_list}. Deferred courses: {deferred}.',
        priority='high',
    )

    return {'enrolled_courses': enrolled, 'warnings': warnings, 'blocked_courses': blocked}


def get_missing_curriculum_registrations(student, curriculum_sem=None) -> list[str]:
    """Curriculum courses not registered — used for promotion checks (ignores fee status)."""
    from students.models import Student

    if isinstance(student, int):
        student = Student.objects.select_related('program').get(student_id=student)

    sem_num = curriculum_sem if curriculum_sem is not None else student.current_semester
    academic_semester = Semester.objects.filter(is_current=True).first()
    if not academic_semester:
        return []

    enrollment = Enrollment.objects.filter(
        student=student, semester=academic_semester,
    ).first()

    missing = []
    for pc in ProgramCourse.objects.filter(
        program=student.program, semester_number=sem_num,
    ).select_related('course'):
        if enrollment and CourseRegistration.objects.filter(
            enrollment=enrollment, course=pc.course, status='registered',
        ).exists():
            continue
        missing.append(pc.course.course_code)
    return missing


def promote_student_after_published_result(student, completed_semester, performed_by=None) -> dict:
    from examinations.models import Result
    from students.models import Student

    with transaction.atomic():
        result = Result.objects.select_for_update().filter(
            student=student, semester=completed_semester, is_published=True,
        ).first()
        if not result:
            return {'promoted': False, 'reason': 'Result not published.'}

        if result.status == 'fail':
            return {'promoted': False, 'reason': 'Student failed semester; manual review required.'}

        if result.promotion_applied and not result.promotion_pending:
            from enrollments.progress_utils import student_ready_for_curriculum_promotion
            if student_ready_for_curriculum_promotion(student, completed_semester):
                result.promotion_applied = False
                result.save(update_fields=['promotion_applied'])
            else:
                return {'promoted': False, 'reason': 'Promotion already applied for this result.'}

        if result.promotion_applied and not result.promotion_pending:
            return {'promoted': False, 'reason': 'Promotion already applied for this result.'}

        student = Student.objects.select_for_update().select_related('program').get(
            pk=student.pk,
        )

        if result.promotion_pending and result.pending_promotion_semester:
            next_sem_num = result.pending_promotion_semester
            if student.current_semester != next_sem_num - 1:
                return {
                    'promoted': False,
                    'reason': (
                        f'Student is on curriculum semester {student.current_semester}; '
                        f'pending promotion targets semester {next_sem_num}.'
                    ),
                }
        else:
            next_sem_num = student.current_semester + 1

        policy = get_academic_policy()
        if not policy.soft_prerequisite_enrollment:
            missing = get_missing_curriculum_registrations(student)
            if missing:
                codes = ', '.join(missing)
                return {
                    'promoted': False,
                    'reason': f'Curriculum courses not registered: {codes}.',
                }

        max_sem = ProgramCourse.objects.filter(program=student.program).order_by(
            '-semester_number',
        ).values_list('semester_number', flat=True).first()

        if max_sem and next_sem_num > max_sem:
            from students.degree_audit import run_degree_audit
            audit = run_degree_audit(student)
            if not audit['eligible']:
                return {
                    'promoted': False,
                    'reason': 'Degree audit incomplete — admin must confirm graduation.',
                    'graduation_blocked': True,
                    'audit': audit,
                }
            student.status = 'graduated'
            student.graduation_date = timezone.now().date()
            student.save(update_fields=['status', 'graduation_date'])
            result.promotion_applied = True
            result.promotion_pending = False
            result.pending_promotion_semester = None
            result.save(update_fields=['promotion_applied', 'promotion_pending', 'pending_promotion_semester'])
            return {'promoted': False, 'reason': 'Program completed.', 'graduated': True}

        next_semester = Semester.objects.filter(is_current=True).first()
        if not next_semester:
            student.current_semester = next_sem_num
            student.save(update_fields=['current_semester'])
            result.promotion_applied = True
            result.promotion_pending = False
            result.pending_promotion_semester = None
            result.save(update_fields=['promotion_applied', 'promotion_pending', 'pending_promotion_semester'])
            return {
                'promoted': True,
                'current_semester': next_sem_num,
                'enrollment': None,
                'reason': 'No current semester set for enrollment.',
            }

        enroll_stats = enroll_student_for_semester(
            student, next_semester, performed_by, curriculum_semester=next_sem_num,
        )
        if enroll_stats.get('registration_blocked'):
            result.promotion_pending = True
            result.pending_promotion_semester = next_sem_num
            result.save(update_fields=['promotion_pending', 'pending_promotion_semester'])
            return {
                'promoted': False,
                'reason': (
                    f'Semester {next_sem_num} fee unpaid — promotion pending; '
                    'courses will enroll automatically when fee is paid.'
                ),
                'promotion_pending': True,
                'pending_promotion_semester': next_sem_num,
                'registration_blocked': True,
                'current_semester': student.current_semester,
                **enroll_stats,
            }

        student.current_semester = next_sem_num
        student.save(update_fields=['current_semester'])
        from enrollments.repeat_utils import reconcile_repeat_registrations
        reconcile_repeat_registrations(student)
        result.promotion_applied = True
        result.promotion_pending = False
        result.pending_promotion_semester = None
        result.save(update_fields=[
            'promotion_applied', 'promotion_pending', 'pending_promotion_semester',
        ])
        return {
            'promoted': True,
            'current_semester': next_sem_num,
            **enroll_stats,
        }


def try_complete_pending_promotion(student, academic_semester, curriculum_semester, performed_by=None):
    """
    Complete admin-approved promotion after finance marks the target semester fee paid.
    Returns promotion outcome dict, or None when no pending promotion applies.
    """
    from examinations.models import Result

    has_pending = Result.objects.filter(
        student=student,
        semester=academic_semester,
        is_published=True,
        promotion_pending=True,
        pending_promotion_semester=curriculum_semester,
    ).exists()
    if not has_pending:
        return None
    return promote_student_after_published_result(student, academic_semester, performed_by)


def _ensure_semester_challan(student, program, semester, sem_num, performed_by):
    if Challan.objects.filter(
        student=student, semester=semester, curriculum_semester=sem_num,
    ).exists():
        return None
    fee_structure = FeeStructure.objects.filter(
        program=program, semester_number=sem_num, fee_type='semester_fee',
    ).order_by('-effective_from').first()
    amount = fee_structure.amount if fee_structure else (program.fee_per_semester or 75000)
    challan = Challan.objects.create(
        challan_number=f"CH-{timezone.now().year}-{str(uuid.uuid4().int)[:6]}",
        student=student,
        semester=semester,
        curriculum_semester=sem_num,
        due_date=timezone.now().date() + timedelta(days=30),
        total_amount=amount,
        generated_by=performed_by,
    )
    from notifications.system_notify import notify_user
    notify_user(
        student.user,
        'Finance',
        f'Semester {sem_num} fee challan issued',
        (
            f'Challan {challan.challan_number} for Rs {challan.total_amount:,.0f} is pending. '
            'Pay at the Finance office to register your courses.'
        ),
        priority='high',
    )
    return challan


def revoke_unpaid_curriculum_registrations(student, academic_semester, curriculum_semester) -> int:
    """
    Drop active regular curriculum registrations when fee for that curriculum semester
    has not been paid. Repeat/carry-over courses are left unchanged.
    """
    from enrollments.progress_utils import is_regular_course_for_student
    from enrollments.repeat_utils import sync_offering_enrolled_count

    enrollment = Enrollment.objects.filter(student=student, semester=academic_semester).first()
    if not enrollment:
        return 0

    removed = 0
    regs = CourseRegistration.objects.filter(
        enrollment=enrollment,
        status='registered',
    ).select_related('course', 'offering')
    for reg in regs:
        if not is_regular_course_for_student(student, reg.course, curriculum_semester):
            continue
        if reg.offering_id:
            sync_offering_enrolled_count(reg.offering)
        reg.delete()
        removed += 1

    enrollment.total_credit_hours_registered = _all_registered_credit_hours(enrollment)
    if enrollment.total_credit_hours_registered == 0 and not CourseRegistration.objects.filter(
        enrollment=enrollment, status='registered',
    ).exists():
        enrollment.status = 'withdrawn'
        enrollment.save(update_fields=['total_credit_hours_registered', 'status'])
    else:
        enrollment.save(update_fields=['total_credit_hours_registered'])
    return removed
