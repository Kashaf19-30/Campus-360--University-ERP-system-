"""Resolve program-scoped teacher assignments for enrollment offerings."""
from __future__ import annotations

from django.db import IntegrityError
from django.db.models import Max

from academics.models import CourseOffering
from academics.session_utils import curriculum_semester_for_course
from faculty.models import FacultyCourseAssignment


def assign_faculty_to_course(faculty, program, course, assigned_by=None):
    """
    Assign (or re-assign) a teacher to a program+course.
    Reactivates soft-deleted rows instead of inserting duplicates.
    """
    existing = FacultyCourseAssignment.objects.filter(program=program, course=course).first()
    if existing:
        if existing.is_active and existing.faculty_id != faculty.faculty_id:
            raise ValueError(
                f'{course.course_code} already has a teacher for {program.program_code}.'
            )
        existing.faculty = faculty
        existing.is_active = True
        existing.assigned_by = assigned_by
        existing.save(update_fields=['faculty', 'is_active', 'assigned_by'])
        return existing, False

    try:
        return FacultyCourseAssignment.objects.create(
            faculty=faculty,
            program=program,
            course=course,
            assigned_by=assigned_by,
        ), True
    except IntegrityError:
        existing = FacultyCourseAssignment.objects.get(program=program, course=course)
        if existing.is_active and existing.faculty_id != faculty.faculty_id:
            raise ValueError(
                f'{course.course_code} already has a teacher for {program.program_code}.'
            ) from None
        existing.faculty = faculty
        existing.is_active = True
        existing.assigned_by = assigned_by
        existing.save(update_fields=['faculty', 'is_active', 'assigned_by'])
        return existing, False


def get_assigned_faculty(course, program):
    assignment = FacultyCourseAssignment.objects.filter(
        program=program, course=course, is_active=True,
    ).select_related('faculty').first()
    return assignment.faculty if assignment else None


def offering_is_reusable_for_enrollment(offering, curriculum_semester) -> bool:
    """
    True when new regular students can join this offering.
    Empty or finished classes (prior cohort promoted) are not reused.
    """
    if not offering or not offering.is_active:
        return False
    from enrollments.repeat_utils import roster_eligible_registrations

    regs = roster_eligible_registrations(offering).select_related('student')
    if not regs.exists():
        return False
    return all(reg.student.current_semester == curriculum_semester for reg in regs)


def _offering_queryset(
    course, semester, faculty, curriculum_semester, repeat_offering, *, is_active=True,
):
    qs = CourseOffering.objects.filter(
        course=course,
        semester=semester,
        faculty=faculty,
        curriculum_semester=curriculum_semester,
        repeat_offering=repeat_offering,
    )
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.order_by('-cohort_sequence', '-offering_id')


def _find_reusable_regular_offering(course, semester, faculty, curriculum_semester):
    for offering in _offering_queryset(
        course, semester, faculty, curriculum_semester, repeat_offering=False,
    ):
        if offering_is_reusable_for_enrollment(offering, curriculum_semester):
            return offering
    return None


def _find_repeat_offering(course, semester, faculty, curriculum_semester):
    """Repeat sections intentionally mix students from different curriculum stages."""
    return _offering_queryset(
        course, semester, faculty, curriculum_semester, repeat_offering=True,
    ).first()


def _next_cohort_sequence(course, semester, faculty, curriculum_semester, repeat_offering) -> int:
    current = _offering_queryset(
        course, semester, faculty, curriculum_semester, repeat_offering, is_active=None,
    ).aggregate(max_seq=Max('cohort_sequence'))['max_seq']
    return (current or 0) + 1


def _create_offering(course, semester, faculty, curriculum_semester, repeat_offering):
    offering = CourseOffering.objects.create(
        course=course,
        semester=semester,
        faculty=faculty,
        curriculum_semester=curriculum_semester,
        repeat_offering=repeat_offering,
        cohort_sequence=_next_cohort_sequence(
            course, semester, faculty, curriculum_semester, repeat_offering,
        ),
        offering_type='theory',
        is_active=True,
    )
    from examinations.assessment_setup import ensure_offering_assessments
    ensure_offering_assessments(offering)
    return offering


def resolve_offering_for_enrollment(
    course, program, semester, warnings, notify_user=None, *,
    curriculum_semester=None, repeat_offering=False,
):
    """
    Pick or create a CourseOffering using the teacher assigned to this program+course.
    Regular offerings auto-split when the previous cohort has finished and moved on.
    Returns None and appends to warnings if no teacher is assigned.
    """
    sem_num = curriculum_semester or curriculum_semester_for_course(program, course)
    faculty = get_assigned_faculty(course, program)
    if not faculty:
        warnings.append(
            f'No teacher assigned for {course.course_code} ({program.program_code}). '
            'Assign a teacher in Teacher Course Management.'
        )
        if notify_user:
            _notify_missing_teacher(notify_user, course, program)
        return None

    if repeat_offering:
        offering = _find_repeat_offering(course, semester, faculty, sem_num)
        if not offering:
            offering = _create_offering(course, semester, faculty, sem_num, repeat_offering=True)
        else:
            from examinations.assessment_setup import ensure_offering_assessments
            ensure_offering_assessments(offering)
        return offering

    offering = _find_reusable_regular_offering(course, semester, faculty, sem_num)
    if not offering:
        offering = _create_offering(course, semester, faculty, sem_num, repeat_offering=False)
    return offering


def pick_offering_for_student(
    course, program, semester, student, warnings, *,
    curriculum_semester=None, repeat_offering=False,
):
    """Prefer a live cohort offering with assigned faculty for the curriculum semester."""
    sem_num = curriculum_semester or curriculum_semester_for_course(program, course)
    faculty = get_assigned_faculty(course, program)
    if faculty:
        if repeat_offering:
            offering = _find_repeat_offering(course, semester, faculty, sem_num)
        else:
            offering = _find_reusable_regular_offering(course, semester, faculty, sem_num)
        if not offering:
            offering = resolve_offering_for_enrollment(
                course, program, semester, warnings,
                curriculum_semester=sem_num,
                repeat_offering=repeat_offering,
            )
        if offering:
            return offering

    if repeat_offering:
        return CourseOffering.objects.filter(
            course=course,
            semester=semester,
            curriculum_semester=sem_num,
            repeat_offering=True,
            is_active=True,
        ).order_by('-cohort_sequence', '-offering_id').first()

    for offering in CourseOffering.objects.filter(
        course=course,
        semester=semester,
        curriculum_semester=sem_num,
        repeat_offering=False,
        is_active=True,
    ).order_by('-cohort_sequence', '-offering_id'):
        if offering_is_reusable_for_enrollment(offering, sem_num):
            return offering
    return CourseOffering.objects.filter(
        course=course,
        semester=semester,
        curriculum_semester=sem_num,
        repeat_offering=False,
        is_active=True,
    ).order_by('-cohort_sequence', '-offering_id').first()


def _notify_missing_teacher(admin_user, course, program):
    from notifications.system_notify import notify_user
    notify_user(
        admin_user,
        'Academic',
        'Missing teacher assignment',
        (
            f'No teacher is assigned for {course.course_code} '
            f'in {program.program_name}. Enrolled students may be pending.'
        ),
        priority='high',
    )
