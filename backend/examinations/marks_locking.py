"""
Marks editability for examinations.

Offering-level lock (marks_locked / marks_unlock_until) applies after teacher submits
final marks. Per-student MarksEditPermission can override that lock.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from accounts.rbac import user_has_permission

PERIOD_PRE_MID = 'pre_mid'
PERIOD_MID_TERM = 'mid_term'
PERIOD_POST_MID = 'post_mid'
PERIOD_FINAL = 'final'

FIRST_HALF_PERIODS = {PERIOD_PRE_MID, PERIOD_MID_TERM}
SECOND_HALF_PERIODS = {PERIOD_POST_MID, PERIOD_FINAL}

PHASE_FIRST_HALF = 'first_half'
PHASE_SECOND_HALF = 'second_half'
PHASE_GRACE = 'grace'
PHASE_ARCHIVED = 'archived'

PERIOD_LABELS = {
    PERIOD_PRE_MID: 'Continuous Assessment (quizzes, assignments, presentations)',
    PERIOD_MID_TERM: 'Mid Term Exam',
    PERIOD_POST_MID: 'Continuous Assessment',
    PERIOD_FINAL: 'Final Term Exam',
}


def _today() -> date:
    return timezone.now().date()


def get_mid_term_cutoff(semester) -> date:
    if semester.mid_term_cutoff_date:
        return semester.mid_term_cutoff_date
    total = (semester.end_date - semester.start_date).days
    return semester.start_date + timedelta(days=max(total // 2, 1))


def get_grace_end(semester) -> date:
    if semester.marks_grace_end_date:
        return semester.marks_grace_end_date
    return semester.end_date + timedelta(days=7)


def get_semester_phase(semester, on_date: date | None = None) -> str:
    today = on_date or _today()
    mid = get_mid_term_cutoff(semester)
    grace = get_grace_end(semester)

    if today < mid:
        return PHASE_FIRST_HALF
    if today <= semester.end_date:
        return PHASE_SECOND_HALF
    if today <= grace:
        return PHASE_GRACE
    return PHASE_ARCHIVED


def resolve_marks_period(exam_type) -> str:
    if exam_type.marks_period:
        return exam_type.marks_period
    name = (exam_type.type_name or '').lower()
    if 'continuous' in name or 'quiz' in name or 'assignment' in name or 'presentation' in name:
        return PERIOD_PRE_MID
    if 'mid' in name and 'term' in name:
        return PERIOD_MID_TERM
    if 'final' in name:
        return PERIOD_FINAL
    return PERIOD_PRE_MID


def is_period_naturally_editable(marks_period: str, phase: str) -> bool:
    return True


def get_lock_reason(marks_period: str, phase: str) -> str:
    if phase == PHASE_ARCHIVED:
        return 'Semester grace period ended. Request admin approval to edit marks.'
    if phase == PHASE_SECOND_HALF and marks_period in FIRST_HALF_PERIODS:
        return f'Mid-semester passed. {PERIOD_LABELS.get(marks_period, marks_period)} marks are locked.'
    if phase == PHASE_FIRST_HALF and marks_period in SECOND_HALF_PERIODS:
        return f'{PERIOD_LABELS.get(marks_period, marks_period)} opens after mid-semester cutoff.'
    if phase in (PHASE_GRACE, PHASE_ARCHIVED) and marks_period in FIRST_HALF_PERIODS:
        return f'{PERIOD_LABELS.get(marks_period, marks_period)} are locked.'
    return 'Marks are locked for this assessment.'


def offering_bulk_unlock_active(offering) -> bool:
    """True when admin opened a temporary whole-class edit window."""
    if not offering or not offering.marks_unlock_until:
        return False
    return offering.marks_unlock_until > timezone.now()


def offering_teacher_marks_eligible(offering) -> bool:
    """Teacher can enter or re-submit marks for this offering."""
    if not offering or not offering.is_active:
        return False
    if not offering.marks_locked:
        return True
    return offering_bulk_unlock_active(offering)


def offering_submission_locked(offering) -> bool:
    """True when teacher submitted final marks and bulk unlock is not active."""
    if not offering:
        return False
    if offering_bulk_unlock_active(offering):
        return False
    if offering.marks_locked:
        return True
    # Expired temporary unlock window (legacy rows may have marks_locked=False)
    if offering.marks_unlock_until is not None:
        return offering.marks_unlock_until <= timezone.now()
    return False


def has_active_edit_permission(offering, user, student_id, exam) -> bool:
    from examinations.models import MarksEditPermission

    if not user or not student_id or not offering:
        return False
    faculty = getattr(user, 'faculty_profile', None)
    if not faculty:
        return False
    return MarksEditPermission.objects.filter(
        offering=offering,
        student_id=student_id,
        examination=exam,
        granted_to=faculty,
        request_status='approved',
        is_active=True,
        expires_at__gt=timezone.now(),
    ).exists()


def exam_edit_status(exam, user, student_id=None) -> dict:
    """Return editability info for an exam (optionally per student)."""
    period = resolve_marks_period(exam.exam_type)
    phase = get_semester_phase(exam.semester)
    offering = exam.offering
    naturally_editable = is_period_naturally_editable(period, phase)

    result = {
        'exam_id': exam.exam_id,
        'exam_name': exam.exam_name,
        'marks_period': period,
        'semester_phase': phase,
        'mid_term_cutoff': str(get_mid_term_cutoff(exam.semester)),
        'grace_end': str(get_grace_end(exam.semester)),
        'naturally_editable': naturally_editable,
        'editable': naturally_editable,
        'lock_reason': '' if naturally_editable else get_lock_reason(period, phase),
        'offering_locked': offering_submission_locked(offering),
        'offering_bulk_unlock_until': (
            str(offering.marks_unlock_until) if offering and offering.marks_unlock_until else None
        ),
    }

    if user and getattr(user, 'user_type', None) == 'admin':
        result['editable'] = True
        result['lock_reason'] = ''
        return result

    if student_id and user and has_active_edit_permission(offering, user, student_id, exam):
        result['editable'] = True
        result['lock_reason'] = ''
        result['admin_override'] = True
        return result

    if offering_submission_locked(offering):
        result['editable'] = False
        result['lock_reason'] = (
            'Final marks submitted for this course. Request admin approval to edit.'
        )
        return result

    if naturally_editable:
        return result

    return result


def can_edit_exam_marks(exam, user, student_id) -> tuple[bool, str]:
    if not user or not user.is_authenticated:
        return False, 'Authentication required.'
    if user.user_type == 'admin':
        return True, ''

    if user.user_type == 'teacher':
        if not user_has_permission(user, 'examinations.enter_marks'):
            return False, 'You do not have permission to enter or edit marks.'
        faculty = getattr(user, 'faculty_profile', None)
        if not faculty or exam.offering.faculty_id != faculty.faculty_id:
            return False, 'You can only edit marks for your own courses.'

    status = exam_edit_status(exam, user, student_id=student_id)
    if status['editable']:
        return True, ''
    return False, status['lock_reason']
