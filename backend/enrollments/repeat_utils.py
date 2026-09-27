"""Repeat / failed-course helpers for enrollment display and requests."""
from __future__ import annotations

from django.db.models import Sum

from examinations.models import FinalGrade

from .models import CourseRegistration, RepeatCourseRequest
from .progress_utils import is_regular_course_for_student, is_active_regular_registration


def passed_course_ids(student) -> set:
    """Courses the student has passed on any attempt."""
    return set(
        FinalGrade.objects.filter(
            student=student, status='pass',
        ).values_list('course_id', flat=True)
    )


def withdraw_unapproved_repeat_registrations(student) -> int:
    """
    Drop repeat registrations that lack an approved repeat request for the term.
    Keeps teacher rosters aligned with policy.
    """
    withdrawn = 0
    passed = passed_course_ids(student)
    for reg in CourseRegistration.objects.filter(
        student=student,
        status='registered',
        registration_type__in=['repeat', 'prerequisite_repeat'],
    ).select_related('course', 'enrollment'):
        if reg.course_id in passed:
            reg.status = 'withdrawn'
            reg.save(update_fields=['status'])
            withdrawn += 1
            continue
        approved = RepeatCourseRequest.objects.filter(
            student=student,
            course=reg.course,
            semester=reg.enrollment.semester,
            status='approved',
        ).exists()
        if reg.registration_type == 'repeat' and not approved:
            reg.status = 'withdrawn'
            reg.save(update_fields=['status'])
            withdrawn += 1
            if reg.offering_id:
                sync_offering_enrolled_count(reg.offering)
    return withdrawn


def reconcile_repeat_registrations(student) -> int:
    """
    Mark carry-over and failed courses as repeat (not regular).
    Called after promotion or when loading student enrollment data.
    """
    updated = 0
    withdraw_unapproved_repeat_registrations(student)
    regs = CourseRegistration.objects.filter(
        student=student,
        status='registered',
    ).select_related('course', 'student__program')
    for reg in regs:
        fg = FinalGrade.objects.filter(registration=reg).first()
        should_repeat = False
        if fg and fg.status == 'fail':
            should_repeat = True
        elif reg.registration_type == 'regular' and not is_regular_course_for_student(
            reg.student, reg.course,
        ):
            should_repeat = True
        if should_repeat and reg.registration_type != 'repeat':
            reg.registration_type = 'repeat'
            reg.save(update_fields=['registration_type'])
            updated += 1
    return updated


def active_registrations_for_student(student, academic_semester=None):
    """Registered current-semester curriculum courses (not failed, not repeat)."""
    qs = CourseRegistration.objects.filter(
        student=student,
        status='registered',
    ).select_related(
        'course', 'student', 'student__program', 'offering', 'offering__faculty__user',
        'enrollment__semester',
    )
    if academic_semester:
        qs = qs.filter(enrollment__semester=academic_semester)
    return [reg for reg in qs if is_active_regular_registration(reg)]


def visible_registrations_for_student(student, academic_semester=None):
    """
    All registrations shown on the student My Enrollments page:
    regular curriculum courses plus admin-approved repeat courses.
    """
    qs = CourseRegistration.objects.filter(
        student=student,
        status='registered',
    ).select_related(
        'course', 'student', 'student__program', 'offering', 'offering__faculty__user',
        'enrollment__semester',
    )
    if academic_semester:
        qs = qs.filter(enrollment__semester=academic_semester)

    visible = []
    for reg in qs:
        if is_active_regular_registration(reg):
            visible.append(reg)
            continue
        if reg.registration_type not in ('repeat', 'prerequisite_repeat'):
            continue
        if reg.registration_type == 'repeat' and FinalGrade.objects.filter(
            registration=reg, status='fail',
        ).exists():
            approved = RepeatCourseRequest.objects.filter(
                student=student,
                course=reg.course,
                status='approved',
                semester=reg.enrollment.semester,
            ).exists()
            if not approved:
                continue
        visible.append(reg)
    return visible


def roster_eligible_registrations(offering):
    """
    Registrations visible on teacher roster (attendance / marks):
    regular offering → active regular students only;
    repeat offering → approved repeat students only.
    """
    if not offering:
        return CourseRegistration.objects.none()
    registrations = CourseRegistration.objects.filter(
        offering=offering,
        status='registered',
    )
    if offering.repeat_offering:
        approved_ids = RepeatCourseRequest.objects.filter(
            course_id=offering.course_id,
            semester_id=offering.semester_id,
            status='approved',
        ).values_list('student_id', flat=True)
        registrations = registrations.filter(
            registration_type__in=['repeat', 'prerequisite_repeat'],
            student_id__in=approved_ids,
        )
    else:
        registrations = registrations.filter(registration_type='regular')
    return registrations


def roster_eligible_count(offering) -> int:
    return roster_eligible_registrations(offering).count()


def offering_historical_registrations(offering):
    """
    Students tied to this offering (currently enrolled or already graded).
    Used for teacher dashboard enrolled counts after marks submission.
    """
    if not offering:
        return CourseRegistration.objects.none()
    qs = CourseRegistration.objects.filter(
        offering=offering,
        status__in=['registered', 'completed'],
    )
    if offering.repeat_offering:
        qs = qs.filter(registration_type__in=['repeat', 'prerequisite_repeat'])
    else:
        qs = qs.filter(registration_type='regular')
    return qs


def offering_enrolled_count(offering) -> int:
    return offering_historical_registrations(offering).count()


def offering_teaching_complete(offering) -> bool:
    """True when final marks have been submitted or all roster students are graded."""
    if not offering:
        return False
    if offering.marks_locked:
        return True
    historical = offering_historical_registrations(offering)
    if not historical.exists():
        return False
    if roster_eligible_registrations(offering).exists():
        return False
    graded_ids = set(
        FinalGrade.objects.filter(
            registration__offering=offering,
        ).values_list('registration_id', flat=True)
    )
    return all(reg.registration_id in graded_ids for reg in historical)


def offering_is_empty_shell(offering) -> bool:
    """True when offering has no students and no submitted teaching history."""
    if not offering or not offering.is_active:
        return False
    if offering.marks_locked:
        return False
    if roster_eligible_registrations(offering).exists():
        return False
    return not offering_historical_registrations(offering).exists()


def maybe_deactivate_empty_offering(offering) -> bool:
    """Deactivate abandoned cohort shells with zero roster activity."""
    if not offering_is_empty_shell(offering):
        return False
    offering.is_active = False
    offering.save(update_fields=['is_active'])
    return True


def sync_offering_enrolled_count(offering) -> int:
    """Keep offering.enrolled_count aligned with students on this offering."""
    if not offering:
        return 0
    actual = offering_enrolled_count(offering)
    if offering.enrolled_count != actual:
        offering.enrolled_count = actual
        offering.save(update_fields=['enrolled_count'])
    maybe_deactivate_empty_offering(offering)
    return actual


def prepare_offering_for_new_registration(offering, registration_type='regular') -> None:
    """Repeat/improvement attempts reuse an offering but need a fresh marks cycle."""
    if not offering:
        return
    if registration_type in ('repeat', 'prerequisite_repeat') and offering.marks_locked:
        offering.marks_locked = False
        offering.marks_unlock_until = None
        offering.save(update_fields=['marks_locked', 'marks_unlock_until'])


def enroll_approved_repeat_request(repeat_req, performed_by=None):
    """Register (or activate) a student on an approved repeat course request."""
    from enrollments.models import Enrollment
    from enrollments.promotion import _register_course, _can_add_course
    from academics.policy_utils import get_academic_policy
    from faculty.assignment_utils import pick_offering_for_student

    student = repeat_req.student
    semester = repeat_req.semester
    course = repeat_req.course
    program = student.program
    warnings = []

    enrollment, _ = Enrollment.objects.get_or_create(
        student=student,
        semester=semester,
        defaults={'status': 'enrolled'},
    )
    if enrollment.status != 'enrolled':
        enrollment.status = 'enrolled'
        enrollment.save(update_fields=['status'])

    existing = CourseRegistration.objects.filter(
        enrollment=enrollment,
        course=course,
    ).select_related('offering').first()

    if existing:
        update_fields = []
        if existing.status in ('dropped', 'withdrawn'):
            existing.status = 'registered'
            update_fields.append('status')
        elif existing.status != 'registered':
            existing.status = 'registered'
            update_fields.append('status')
        if existing.registration_type != 'repeat':
            existing.registration_type = 'repeat'
            update_fields.append('registration_type')

        repeat_offering = pick_offering_for_student(
            course, program, semester, student, warnings,
            repeat_offering=True,
        )
        if repeat_offering and existing.offering_id != repeat_offering.offering_id:
            prepare_offering_for_new_registration(repeat_offering, 'repeat')
            if existing.offering_id:
                sync_offering_enrolled_count(existing.offering)
            existing.offering = repeat_offering
            update_fields.append('offering')
        elif not existing.offering_id and repeat_offering:
            prepare_offering_for_new_registration(repeat_offering, 'repeat')
            existing.offering = repeat_offering
            update_fields.append('offering')
        if existing.offering_id:
            prepare_offering_for_new_registration(existing.offering, 'repeat')
            sync_offering_enrolled_count(existing.offering)
        if update_fields:
            existing.save(update_fields=update_fields)
        return {
            'registration_id': existing.registration_id,
            'course_code': course.course_code,
            'created': False,
            'warnings': warnings,
        }

    policy = get_academic_policy()
    if not _can_add_course(enrollment, course, policy):
        return {
            'error': f'Credit cap exceeded — cannot register repeat {course.course_code}.',
            'warnings': warnings,
        }

    offering = pick_offering_for_student(
        course, program, semester, student, warnings,
        repeat_offering=True,
    )
    if not offering:
        return {
            'error': f'No offering available for {course.course_code}. Assign a teacher first.',
            'warnings': warnings,
        }

    prepare_offering_for_new_registration(offering, 'repeat')
    _register_course(
        enrollment, student, course, offering, registration_type='repeat',
    )
    sync_offering_enrolled_count(offering)
    return {
        'registration_id': None,
        'course_code': course.course_code,
        'created': True,
        'warnings': warnings,
    }


def failed_course_ids_for_repeat_request(student, current_semester) -> set[int]:
    """Course IDs with a fail grade that are not already pending/approved for repeat."""
    blocked = set(
        RepeatCourseRequest.objects.filter(
            student=student,
            semester=current_semester,
            status__in=['pending', 'approved'],
        ).values_list('course_id', flat=True)
    )
    passed = passed_course_ids(student)
    return set(
        FinalGrade.objects.filter(student=student, status='fail')
        .exclude(course_id__in=blocked)
        .exclude(course_id__in=passed)
        .values_list('course_id', flat=True)
    )


def eligible_failed_courses_for_repeat(student, current_semester):
    """
    Failed courses the student may request to repeat in the current academic term.
    Includes failures from any published term (not only the previous semester).
    """
    from academics.policy_utils import get_academic_policy
    from academics.session_utils import format_curriculum_semester, curriculum_semester_for_course
    from .promotion import _semester_fee_paid, get_student_semester_credit_summary

    policy = get_academic_policy()
    fee_paid = _semester_fee_paid(student, current_semester)
    enrollment = student.enrollments.filter(semester=current_semester).first()
    summary = get_student_semester_credit_summary(student, current_semester)
    enrolled_ch = summary['enrolled_credit_hours']
    pending_repeat_ch = RepeatCourseRequest.objects.filter(
        student=student,
        semester=current_semester,
        status__in=['pending', 'approved'],
    ).aggregate(total=Sum('course__credit_hours'))['total'] or 0

    blocked_course_ids = set(
        RepeatCourseRequest.objects.filter(
            student=student,
            semester=current_semester,
            status__in=['pending', 'approved'],
        ).values_list('course_id', flat=True)
    )

    passed_ids = passed_course_ids(student)
    failed_grades = FinalGrade.objects.filter(
        student=student,
        status='fail',
    ).exclude(
        course_id__in=passed_ids,
    ).select_related('course', 'semester').order_by('-semester__academic_year', 'course__course_code')

    seen_course_ids = set()
    failed_list = []
    for fg in failed_grades:
        if fg.course_id in seen_course_ids or fg.course_id in blocked_course_ids:
            continue
        seen_course_ids.add(fg.course_id)

        would_total = enrolled_ch + pending_repeat_ch + fg.course.credit_hours
        can_request = fee_paid and would_total <= policy.max_semester_credit_hours
        repeat_cap_ok = pending_repeat_ch + fg.course.credit_hours <= policy.max_repeat_credit_hours
        if not repeat_cap_ok:
            can_request = False
        block_reason = ''
        if not fee_paid:
            block_reason = 'Semester fee must be paid before requesting repeat courses.'
            can_request = False
        elif not can_request:
            if not repeat_cap_ok:
                block_reason = f'Repeat credit limit ({policy.max_repeat_credit_hours} CH) would be exceeded.'
            else:
                block_reason = (
                    f'Semester credit cap ({policy.max_semester_credit_hours} CH) — '
                    f'you have {enrolled_ch} CH enrolled; this course needs {fg.course.credit_hours} CH free.'
                )
        failed_list.append({
            'course_id': fg.course_id,
            'course_code': fg.course.course_code,
            'course_name': fg.course.course_name,
            'credit_hours': fg.course.credit_hours,
            'failed_semester': format_curriculum_semester(
                curriculum_semester_for_course(student.program, fg.course),
            ),
            'can_request': can_request,
            'block_reason': block_reason,
        })

    return failed_list


def ensure_curriculum_enrolled_if_paid(student, academic_semester):
    """
    Self-heal: if a paid challan exists but curriculum courses were never registered
    (e.g. finance marked paid before the enrollment-order bug was fixed), enroll now.
    """
    from fees.models import Challan
    from academics.models import ProgramCourse
    from accounts.models import User
    from enrollments.promotion import enroll_student_for_semester

    if not academic_semester:
        return []

    admin = User.objects.filter(user_type='admin', is_active=True).first()
    outcomes = []
    for challan in Challan.objects.filter(
        student=student, semester=academic_semester, status='paid',
    ):
        sem_num = challan.curriculum_semester
        missing = []
        for pc in ProgramCourse.objects.filter(
            program=student.program, semester_number=sem_num,
        ).select_related('course'):
            if not is_regular_course_for_student(student, pc.course, sem_num):
                continue
            has_reg = CourseRegistration.objects.filter(
                student=student,
                course=pc.course,
                status='registered',
                enrollment__semester=academic_semester,
            ).exists()
            if not has_reg:
                missing.append(pc.course.course_code)
        if missing:
            stats = enroll_student_for_semester(
                student,
                academic_semester,
                performed_by=admin or student.user,
                curriculum_semester=sem_num,
            )
            outcomes.append({'curriculum_semester': sem_num, **stats})
    return outcomes
