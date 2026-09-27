"""Academic policy helpers — configurable GPA thresholds and standing updates."""
from __future__ import annotations

from decimal import Decimal

from notifications.models import Notification, NotificationType


DEFAULT_MIN_SGPA = Decimal('2.0')
DEFAULT_MIN_CGPA = Decimal('2.0')
DEFAULT_MAX_CONSECUTIVE_PROBATION = 2


def get_academic_policy():
    from academics.models import AcademicPolicy
    policy, _ = AcademicPolicy.objects.get_or_create(pk=1)
    return policy


def semester_status_from_sgpa(sgpa: Decimal, fail_count: int, policy=None) -> str:
    """
    Semester standing from SGPA only (failed courses still require repeat separately).
    Probation applies when SGPA is below the pass threshold, not merely because a course failed.
    """
    policy = policy or get_academic_policy()
    if sgpa >= policy.min_sgpa_pass:
        return 'pass'
    if sgpa >= policy.min_sgpa_probation:
        return 'probation'
    return 'fail'


def apply_standing_after_publish(student, result, *, performed_by=None) -> dict:
    """
    Update consecutive probation counter and dismissal-review flag when a result is published.
    """
    policy = get_academic_policy()
    updates = {'consecutive_probation_count': student.consecutive_probation_count}

    if result.status == 'pass':
        student.consecutive_probation_count = 0
        student.academic_review_required = False
    elif result.status == 'probation':
        student.consecutive_probation_count += 1
        if student.consecutive_probation_count >= policy.max_consecutive_probation:
            student.academic_review_required = True
    elif result.status == 'fail':
        student.consecutive_probation_count = 0

    student.save(update_fields=['consecutive_probation_count', 'academic_review_required'])

    notified = False
    if student.academic_review_required and performed_by:
        notif_type, _ = NotificationType.objects.get_or_create(
            type_name='Academic',
            defaults={'description': 'Academic updates'},
        )
        Notification.objects.create(
            notification_type=notif_type,
            recipient=student.user,
            title='Academic review required',
            message=(
                f'You have been on probation for {student.consecutive_probation_count} consecutive '
                f'semester(s). Please contact the administration for academic advising.'
            ),
            priority='high',
        )
        notified = True

    return {
        'consecutive_probation_count': student.consecutive_probation_count,
        'academic_review_required': student.academic_review_required,
        'notified': notified,
    }


def can_graduate(student, policy=None) -> tuple[bool, str]:
    policy = policy or get_academic_policy()
    if student.cgpa < policy.min_cgpa_graduation:
        return False, f'CGPA {student.cgpa} is below minimum {policy.min_cgpa_graduation} for graduation.'
    return True, ''
