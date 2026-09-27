"""Single active session helpers — curriculum semester is the user-facing concept."""
from __future__ import annotations

from .models import Semester


def get_active_session():
    """Internal active session record (not shown as Fall/Spring in the UI)."""
    return Semester.objects.filter(is_current=True).first()


def format_curriculum_semester(semester_number) -> str:
    if semester_number is None:
        return '—'
    return f'Semester {semester_number}'


def curriculum_semester_for_course(program, course) -> int:
    from .models import ProgramCourse

    sem = ProgramCourse.objects.filter(
        program=program,
        course=course,
    ).order_by('semester_number').values_list('semester_number', flat=True).first()
    return sem or 1
