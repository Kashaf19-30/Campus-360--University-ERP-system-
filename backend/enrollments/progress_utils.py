"""Semester progress, repeat monitoring, and batch promotion helpers."""
from __future__ import annotations

from collections import defaultdict

from academics.models import ProgramCourse, Semester, CourseOffering
from enrollments.models import CourseRegistration
from examinations.models import FinalGrade
from students.models import Student


def get_current_academic_semester():
    from academics.session_utils import get_active_session
    return get_active_session()


def is_regular_course_for_student(student, course, curriculum_semester=None):
    sem_num = curriculum_semester if curriculum_semester is not None else student.current_semester
    return ProgramCourse.objects.filter(
        program=student.program,
        course=course,
        semester_number=sem_num,
    ).exists()


def is_active_regular_registration(reg) -> bool:
    """Current-semester curriculum course still in progress (not failed)."""
    if reg.status != 'registered':
        return False
    if not is_regular_course_for_student(reg.student, reg.course):
        return False
    if FinalGrade.objects.filter(registration=reg, status='fail').exists():
        return False
    return True


def _progress_registrations(offering):
    """Roster for academic progress — includes students already graded (completed)."""
    from enrollments.repeat_utils import offering_historical_registrations, roster_eligible_registrations

    if not offering:
        return CourseRegistration.objects.none()
    historical = offering_historical_registrations(offering)
    active = roster_eligible_registrations(offering)
    return (historical | active).distinct()


def _offering_completion(offering_id):
    """Return completion stats for an offering's teacher-visible roster."""
    from examinations.assessment_setup import get_offering_weight_allocation_status

    offering = CourseOffering.objects.select_related(
        'course', 'faculty__user', 'semester',
    ).filter(pk=offering_id).first()
    regs = _progress_registrations(offering)
    total = regs.count()
    weight = get_offering_weight_allocation_status(offering) if offering else {
        'weight_complete': False,
        'total_allocated': 0,
        'required_total': 100,
    }

    if total == 0:
        return {
            'offering_id': offering_id,
            'course_code': offering.course.course_code if offering else '',
            'course_name': offering.course.course_name if offering else '',
            'teacher_name': offering.faculty.user.username if offering and offering.faculty_id else 'Unassigned',
            'semester_name': offering.semester.semester_name if offering else '',
            'marks_locked': bool(offering and offering.marks_locked),
            'total_students': 0,
            'graded_students': 0,
            'pending_students': 0,
            'weight_allocated': weight['total_allocated'],
            'weight_complete': weight['weight_complete'],
            'is_complete': weight['weight_complete'],
            'status': 'weight_incomplete' if not weight['weight_complete'] else 'completed',
            'promotion_block_reason': (
                '' if weight['weight_complete']
                else f'Assessment weights total {weight["total_allocated"]:.0f}% — must be 100% for promotion eligibility.'
            ),
        }
    graded = FinalGrade.objects.filter(
        registration_id__in=regs.values_list('registration_id', flat=True),
    ).count()
    pending = total - graded
    grades_ready = pending == 0 and bool(offering and offering.marks_locked)
    is_complete = weight['weight_complete'] and grades_ready
    if not weight['weight_complete']:
        status = 'weight_incomplete'
        promotion_block_reason = (
            f'Assessment weights total {weight["total_allocated"]:.0f}% — '
            'complete Step 2 weightage (100% required) for promotion eligibility.'
        )
    elif not grades_ready:
        status = 'pending'
        promotion_block_reason = 'Final marks not submitted for all enrolled students.'
    else:
        status = 'completed'
        promotion_block_reason = ''
    return {
        'offering_id': offering_id,
        'course_code': offering.course.course_code if offering else '',
        'course_name': offering.course.course_name if offering else '',
        'teacher_name': offering.faculty.user.username if offering and offering.faculty_id else 'Unassigned',
        'semester_name': offering.semester.semester_name if offering else '',
        'marks_locked': bool(offering and offering.marks_locked),
        'total_students': total,
        'graded_students': graded,
        'pending_students': pending,
        'weight_allocated': weight['total_allocated'],
        'weight_complete': weight['weight_complete'],
        'is_complete': is_complete,
        'status': status,
        'promotion_block_reason': promotion_block_reason,
    }


def get_semester_progress(curriculum_semester, academic_semester=None):
    """
    Section A — regular curriculum courses for students in curriculum_semester.
    Repeat registrations are excluded.
    """
    academic_semester = academic_semester or get_current_academic_semester()
    students = Student.objects.filter(
        current_semester=curriculum_semester,
        status='active',
    ).select_related('program')
    student_ids = list(students.values_list('student_id', flat=True))
    student_count = len(student_ids)

    if not academic_semester or not student_ids:
        return {
            'curriculum_semester': curriculum_semester,
            'academic_semester': _semester_payload(academic_semester),
            'student_count': student_count,
            'regular_courses_total': 0,
            'regular_courses_completed': 0,
            'status': 'in_progress' if student_count else 'no_students',
            'status_label': 'No Students' if not student_count else 'In Progress',
            'courses': [],
            'pending_courses': [],
        }

    regs = CourseRegistration.objects.filter(
        student_id__in=student_ids,
        status__in=['registered', 'completed'],
        enrollment__semester=academic_semester,
    ).select_related('course', 'student__program', 'offering__faculty__user', 'offering__course')

    offering_ids = set()
    for reg in regs:
        if not reg.offering_id:
            continue
        if not is_regular_course_for_student(reg.student, reg.course, curriculum_semester):
            continue
        offering_ids.add(reg.offering_id)

    courses = []
    pending_courses = []
    for oid in sorted(offering_ids):
        comp = _offering_completion(oid)
        courses.append(comp)
        if not comp['is_complete']:
            pending_courses.append({
                **comp,
                'affected_students': comp['pending_students'],
            })

    completed = sum(1 for c in courses if c['is_complete'])
    total = len(courses)
    has_weight_issue = any(
        c.get('total_students', 0) > 0 and not c.get('weight_complete', True)
        for c in courses
    )
    if student_count == 0:
        status = 'no_students'
        label = 'No Students'
    elif total == 0:
        status = 'in_progress'
        label = 'In Progress'
    elif has_weight_issue:
        status = 'not_eligible'
        label = 'Not Eligible for Promotion'
    elif completed == total:
        status = 'ready_for_promotion'
        label = 'Ready for Promotion'
    else:
        status = 'in_progress'
        label = 'Not Eligible for Promotion'

    return {
        'curriculum_semester': curriculum_semester,
        'academic_semester': _semester_payload(academic_semester),
        'student_count': student_count,
        'regular_courses_total': total,
        'regular_courses_completed': completed,
        'status': status,
        'status_label': label,
        'courses': courses,
        'pending_courses': pending_courses,
    }


def _repeat_offering_done(comp) -> bool:
    """Repeat batch finished — hide from admin repeat progress monitoring."""
    if comp.get('is_complete'):
        return True
    if comp.get('status') == 'completed':
        return True
    return (
        bool(comp.get('marks_locked'))
        and comp.get('pending_students', 0) == 0
        and comp.get('graded_students', 0) > 0
    )


def get_repeat_progress(academic_semester=None, curriculum_semester=None):
    """Section B — repeat/improvement courses for the selected curriculum semester."""
    academic_semester = academic_semester or get_current_academic_semester()
    if not academic_semester:
        return {'academic_semester': None, 'curriculum_semester': curriculum_semester, 'items': []}

    regs = CourseRegistration.objects.filter(
        status__in=['registered', 'completed'],
        enrollment__semester=academic_semester,
        registration_type__in=['repeat', 'prerequisite_repeat'],
    ).select_related('student__program', 'course', 'offering__faculty__user')

    if curriculum_semester is not None:
        regs = regs.filter(student__current_semester=curriculum_semester)

    repeat_by_offering = defaultdict(lambda: {'students': set(), 'offering': None})
    for reg in regs:
        if not reg.offering_id:
            continue
        repeat_by_offering[reg.offering_id]['students'].add(reg.student_id)

    items = []
    for oid, data in repeat_by_offering.items():
        comp = _offering_completion(oid)
        if comp['total_students'] == 0 or _repeat_offering_done(comp):
            continue
        items.append({
            **comp,
            'waiting_students': comp['pending_students'],
            'enrolled_students': comp['total_students'],
            'status_label': 'Pending Grades',
        })

    items.sort(key=lambda x: (x.get('course_code', ''), x.get('offering_id', 0)))
    return {
        'academic_semester': _semester_payload(academic_semester),
        'curriculum_semester': curriculum_semester,
        'items': items,
    }


def get_teacher_workflow_warnings(faculty):
    """Pending final grades + courses blocking semester promotion."""
    if not faculty:
        return {'pending_final_grades': [], 'blocking_promotion': []}

    offerings = CourseOffering.objects.filter(
        faculty=faculty,
        is_active=True,
    ).select_related('course', 'semester')

    pending = []
    blocking = []
    incomplete_weights = []
    for offering in offerings:
        comp = _offering_completion(offering.offering_id)
        if comp['total_students'] == 0:
            continue
        if not comp.get('weight_complete', True):
            incomplete_weights.append({
                'offering_id': offering.offering_id,
                'course_code': offering.course.course_code,
                'course_name': offering.course.course_name,
                'weight_allocated': comp.get('weight_allocated', 0),
                'message': comp.get('promotion_block_reason') or (
                    f'Assessment weights must total 100% (currently {comp.get("weight_allocated", 0):.0f}%).'
                ),
            })
        if comp['pending_students'] > 0 or not offering.marks_locked:
            entry = {
                'offering_id': offering.offering_id,
                'course_code': offering.course.course_code,
                'course_name': offering.course.course_name,
                'students_waiting': comp['pending_students'],
                'marks_locked': offering.marks_locked,
                'weight_complete': comp.get('weight_complete', False),
            }
            pending.append(entry)

            regs = CourseRegistration.objects.filter(
                offering=offering,
                status='registered',
            ).select_related('student')
            blocked_sems = set()
            for reg in regs:
                if is_regular_course_for_student(reg.student, reg.course):
                    blocked_sems.add(reg.student.current_semester)
            for sem in blocked_sems:
                prog = get_semester_progress(sem, offering.semester)
                if prog['status'] != 'ready_for_promotion' and not comp['is_complete']:
                    blocking.append({
                        **entry,
                        'curriculum_semester': sem,
                        'message': comp.get('promotion_block_reason') or (
                            f'This course is preventing Semester {sem} '
                            'from becoming eligible for promotion.'
                        ),
                    })
                    break

    return {
        'pending_final_grades': pending,
        'blocking_promotion': blocking,
        'incomplete_weight_allocations': incomplete_weights,
    }


def get_student_academic_status(student):
    """Dashboard summary for a student."""
    from fees.models import Challan

    if student.status == 'graduated':
        return {
            'current_semester': student.current_semester,
            'semester_status': 'Graduated',
            'semester_progress': None,
            'repeat_courses': [],
            'financial_status': 'N/A',
            'registration_blocked': False,
            'registration_block_reason': '',
            'is_graduated': True,
        }

    academic_semester = get_current_academic_semester()
    curriculum_sem = student.current_semester

    progress = get_semester_progress(curriculum_sem, academic_semester)
    repeat_items = []
    if academic_semester:
        regs = CourseRegistration.objects.filter(
            student=student,
            status='registered',
            enrollment__semester=academic_semester,
        ).select_related('course', 'offering__faculty__user')
        for reg in regs:
            if not reg.offering_id:
                continue
            if is_regular_course_for_student(student, reg.course):
                continue
            fg = FinalGrade.objects.filter(registration=reg).first()
            faculty_name = '—'
            if reg.offering and reg.offering.faculty_id and reg.offering.faculty.user_id:
                faculty_name = reg.offering.faculty.user.username
            repeat_items.append({
                'course_code': reg.course.course_code,
                'course_name': reg.course.course_name,
                'teacher_name': faculty_name,
                'status': 'Completed' if fg else 'Waiting for Teacher Submission',
            })

    financial_status = 'Paid'
    registration_blocked = False
    registration_block_reason = ''
    if academic_semester:
        challan = Challan.objects.filter(
            student=student, semester=academic_semester, curriculum_semester=student.current_semester,
        ).first()
        if challan and challan.status != 'paid':
            financial_status = challan.status.title()
            registration_blocked = True
            has_regs = CourseRegistration.objects.filter(
                student=student,
                enrollment__semester=academic_semester,
                status='registered',
            ).exists()
            if not has_regs:
                registration_block_reason = (
                    'Outstanding semester fee. Pay your challan to register courses.'
                )
            else:
                registration_block_reason = (
                    'Outstanding semester fee. Contact the Finance Office.'
                )

    return {
        'current_semester': curriculum_sem,
        'semester_status': progress['status_label'],
        'semester_progress': progress,
        'repeat_courses': repeat_items,
        'financial_status': financial_status,
        'registration_blocked': registration_blocked,
        'registration_block_reason': registration_block_reason,
        'is_graduated': False,
    }


def student_ready_for_curriculum_promotion(student, academic_semester=None) -> bool:
    """True when this student has final marks for all regular courses at their current level."""
    academic_semester = academic_semester or get_current_academic_semester()
    if not academic_semester:
        return False

    regs = CourseRegistration.objects.filter(
        student=student,
        status__in=['registered', 'completed'],
        enrollment__semester=academic_semester,
    ).select_related('course', 'offering')
    regular_regs = [
        reg for reg in regs
        if is_regular_course_for_student(reg.student, reg.course, student.current_semester)
    ]
    if not regular_regs:
        return False

    for reg in regular_regs:
        if not FinalGrade.objects.filter(registration=reg).exists():
            return False
        if reg.offering and not reg.offering.marks_locked:
            return False
    return True


def promote_curriculum_semester_batch(curriculum_semester, academic_semester, performed_by):
    """
    Batch promote all active students in a curriculum semester after regular
    courses are complete. Generates results, publishes, and advances semester.
    """
    from examinations.models import Result, ResultApproval
    from examinations.results_pipeline import ensure_semester_result
    from examinations.views import _publish_single_result

    progress = get_semester_progress(curriculum_semester, academic_semester)
    if progress['status'] != 'ready_for_promotion':
        return {
            'success': False,
            'error': 'Semester is not ready for promotion. Complete all regular courses first.',
            'progress': progress,
        }

    students = Student.objects.filter(current_semester=curriculum_semester, status='active')
    if not students.exists():
        return {'success': False, 'error': 'No active students in this semester.'}

    for student in students:
        ensure_semester_result(student, academic_semester)

    summary = {
        'success': True,
        'curriculum_semester': curriculum_semester,
        'results_generated': {'students_processed': students.count()},
        'promoted': [],
        'held_back': [],
        'graduated': [],
        'promotion_pending': [],
        'registration_blocked': [],
        'skipped': [],
    }

    for student in students:
        try:
            student.refresh_from_db()
            if student.current_semester != curriculum_semester:
                summary['skipped'].append({
                    'registration_number': student.registration_number,
                    'error': 'Already promoted.',
                })
                continue

            result = ensure_semester_result(student, academic_semester)
            if result.status == 'fail':
                summary['held_back'].append({
                    'registration_number': student.registration_number,
                    'student_name': student.user.username,
                    'reason': 'Failed semester — manual review required.',
                })
                continue

            if (
                result.promotion_applied
                and student.current_semester == curriculum_semester
            ):
                result.promotion_applied = False
                result.save(update_fields=['promotion_applied'])

            ResultApproval.objects.get_or_create(
                result=result,
                defaults={'approved_by': performed_by, 'remarks': 'Auto-approved for batch promotion.'},
            )

            if result.is_published:
                if student.current_semester != curriculum_semester:
                    continue
                from enrollments.promotion import promote_student_after_published_result
                promo = promote_student_after_published_result(
                    student, academic_semester, performed_by=performed_by,
                )
            else:
                outcome = _publish_single_result(result, performed_by)
                promo = outcome['promotion']

            entry = {
                'registration_number': student.registration_number,
                'student_name': student.user.username,
            }
            if promo.get('graduated'):
                summary['graduated'].append(entry)
            elif promo.get('promotion_pending'):
                summary['promotion_pending'].append({
                    **entry,
                    'pending_semester': promo.get('pending_promotion_semester'),
                    'reason': promo.get('reason', 'Awaiting semester fee payment.'),
                })
            elif promo.get('registration_blocked'):
                summary['registration_blocked'].append({
                    **entry,
                    'reason': promo.get('reason', 'Fee unpaid — semester not advanced.'),
                })
            elif promo.get('promoted'):
                summary['promoted'].append(entry)
            else:
                summary['held_back'].append({**entry, 'reason': promo.get('reason', 'Not promoted')})
        except Exception as exc:
            summary['skipped'].append({
                'registration_number': student.registration_number,
                'error': str(exc),
            })

    return summary


def _semester_payload(semester):
    if not semester:
        return None
    return {
        'semester_id': semester.semester_id,
        'semester_name': 'Active Session',
        'is_current': semester.is_current,
    }
