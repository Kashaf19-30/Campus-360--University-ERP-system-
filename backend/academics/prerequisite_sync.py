"""Sync course prerequisites from curriculum_prerequisites map."""
from academics.models import Course, CoursePrerequisite
from academics.curriculum_prerequisites import COURSE_PREREQUISITES, ALTERNATIVE_PREREQUISITES


def sync_all_prerequisites():
    """Create/update CoursePrerequisite rows from COURSE_PREREQUISITES."""
    created = 0
    alt_codes = set()
    for alts in ALTERNATIVE_PREREQUISITES.values():
        alt_codes.update(alts)

    for course_code, reqs in COURSE_PREREQUISITES.items():
        course = Course.objects.filter(course_code=course_code).first()
        if not course:
            continue
        CoursePrerequisite.objects.filter(course=course).delete()
        for req in reqs:
            if isinstance(req, dict) and 'credit_hours' in req:
                _, was_created = CoursePrerequisite.objects.get_or_create(
                    course=course,
                    prerequisite_type='credit_hours',
                    min_credit_hours=req['credit_hours'],
                    defaults={'prerequisite_course': None},
                )
                if was_created:
                    created += 1
            elif isinstance(req, str) and req:
                if course_code in ALTERNATIVE_PREREQUISITES and req in alt_codes:
                    continue
                prereq_course = Course.objects.filter(course_code=req).first()
                if not prereq_course:
                    continue
                _, was_created = CoursePrerequisite.objects.get_or_create(
                    course=course,
                    prerequisite_type='course',
                    prerequisite_course=prereq_course,
                    defaults={'min_credit_hours': None},
                )
                if was_created:
                    created += 1
    return created


def sync_program_prerequisites():
    """Seed program-scoped OR prerequisites (e.g. BSCS CS201 needs CS104 OR others CS102)."""
    from academics.models import DegreeProgram, Course, ProgramCoursePrerequisite

    created = 0
    specs = [
        ('BSCS', 'CS201', [('CS104', 1)]),
        ('BSSE', 'CS201', [('CS102', 1)]),
        ('BSAI', 'CS201', [('CS102', 1)]),
        ('BSIT', 'CS201', [('CS102', 1)]),
    ]
    for prog_code, course_code, prereqs in specs:
        program = DegreeProgram.objects.filter(program_code=prog_code).first()
        course = Course.objects.filter(course_code=course_code).first()
        if not program or not course:
            continue
        ProgramCoursePrerequisite.objects.filter(program=program, course=course).delete()
        for p_code, or_group in prereqs:
            p_course = Course.objects.filter(course_code=p_code).first()
            if not p_course:
                continue
            ProgramCoursePrerequisite.objects.create(
                program=program, course=course, prerequisite_course=p_course, or_group=or_group,
            )
            created += 1
    return created
