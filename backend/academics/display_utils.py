"""Safe display helpers for course offerings and faculty."""


def offering_teacher_name(offering, *, default: str = 'Unassigned') -> str:
    if not offering or not offering.faculty_id:
        return default
    faculty = offering.faculty
    if not faculty or not faculty.user_id:
        return default
    return faculty.user.username
