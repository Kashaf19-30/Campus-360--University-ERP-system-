"""Degree completion audit, graduation eligibility, and transcript data."""
from __future__ import annotations

from django.utils import timezone

from academics.models import ProgramCourse
from academics.policy_utils import get_academic_policy, can_graduate
from enrollments.models import CourseRegistration
from examinations.models import FinalGrade, Result
from fees.models import Challan


def _passed_course_ids(student) -> set:
    return set(
        FinalGrade.objects.filter(
            student=student, status='pass',
        ).values_list('course_id', flat=True)
    )


def _course_attempt_count(student, course_id) -> int:
    return CourseRegistration.objects.filter(
        student=student, course_id=course_id,
    ).count()


def run_degree_audit(student) -> dict:
    """
    Full graduation readiness check against curriculum, GPA, fees, and attempts.
    """
    policy = get_academic_policy()
    passed_ids = _passed_course_ids(student)

    curriculum = ProgramCourse.objects.filter(
        program=student.program,
    ).select_related('course').order_by('semester_number', 'course__course_code')

    max_curriculum_sem = curriculum.order_by(
        '-semester_number',
    ).values_list('semester_number', flat=True).first() or 0

    missing_courses = []
    attempt_violations = []
    for pc in curriculum:
        if pc.course_id not in passed_ids:
            missing_courses.append({
                'course_id': pc.course_id,
                'course_code': pc.course.course_code,
                'course_name': pc.course.course_name,
                'semester_number': pc.semester_number,
                'credit_hours': pc.course.credit_hours,
            })
        attempts = _course_attempt_count(student, pc.course_id)
        if attempts > policy.max_course_attempts:
            attempt_violations.append({
                'course_code': pc.course.course_code,
                'attempts': attempts,
                'max_allowed': policy.max_course_attempts,
            })

    outstanding_challans = list(
        Challan.objects.filter(student=student).exclude(
            status='paid',
        ).select_related('semester').values(
            'challan_id', 'challan_number', 'total_amount', 'amount_paid',
            'status', 'semester__semester_name',
        )
    )

    cgpa_ok, cgpa_message = can_graduate(student, policy)

    active_failed_regs = CourseRegistration.objects.filter(
        student=student, status='registered',
    ).exclude(course_id__in=passed_ids).select_related('course')
    pending_failures = [
        {
            'course_code': r.course.course_code,
            'course_name': r.course.course_name,
        }
        for r in active_failed_regs
    ]

    curriculum_complete = len(missing_courses) == 0
    at_final_semester = student.current_semester >= max_curriculum_sem

    issues = []
    if missing_courses:
        issues.append(f'{len(missing_courses)} required course(s) not yet passed.')
    if not cgpa_ok:
        issues.append(cgpa_message)
    if outstanding_challans:
        issues.append(f'{len(outstanding_challans)} outstanding fee challan(s).')
    if attempt_violations:
        issues.append(f'{len(attempt_violations)} course(s) exceeded max attempts.')
    if pending_failures:
        issues.append(f'{len(pending_failures)} course(s) still registered without a pass grade.')
    if student.academic_review_required:
        issues.append('Student is flagged for academic dismissal review.')
    if student.status in ('expelled', 'dropped', 'suspended'):
        issues.append(f'Student status is {student.status}.')

    eligible = (
        student.status == 'active'
        and curriculum_complete
        and cgpa_ok
        and not outstanding_challans
        and not attempt_violations
        and not pending_failures
        and not student.academic_review_required
    )

    total_required = curriculum.count()
    completed_required = total_required - len(missing_courses)
    total_credits = sum(pc.course.credit_hours for pc in curriculum)
    earned_credits = sum(
        pc.course.credit_hours for pc in curriculum if pc.course_id in passed_ids
    )

    return {
        'eligible': eligible,
        'curriculum_complete': curriculum_complete,
        'at_final_semester': at_final_semester,
        'max_curriculum_semester': max_curriculum_sem,
        'issues': issues,
        'missing_courses': missing_courses,
        'outstanding_challans': outstanding_challans,
        'attempt_violations': attempt_violations,
        'pending_failures': pending_failures,
        'cgpa_ok': cgpa_ok,
        'cgpa_message': cgpa_message,
        'cgpa': str(student.cgpa),
        'min_cgpa_graduation': str(policy.min_cgpa_graduation),
        'completed_courses': completed_required,
        'total_courses': total_required,
        'earned_credit_hours': earned_credits,
        'total_credit_hours': total_credits,
        'degree_completion_percent': round(
            (earned_credits / total_credits) * 100, 1,
        ) if total_credits else 0,
    }


def build_transcript(student) -> dict:
    """Structured transcript for display or print."""
    from academics.session_utils import curriculum_semester_for_course, format_curriculum_semester

    def _result_semester_label(result):
        fg = FinalGrade.objects.filter(
            student=student, semester=result.semester,
        ).select_related('course').first()
        if fg:
            return format_curriculum_semester(curriculum_semester_for_course(student.program, fg.course))
        return format_curriculum_semester(student.current_semester)

    audit = run_degree_audit(student)

    grades = FinalGrade.objects.filter(
        student=student,
    ).select_related(
        'course', 'semester', 'grade', 'registration',
    ).order_by('course__course_code')

    by_term = {}
    for fg in grades:
        cur_sem = curriculum_semester_for_course(student.program, fg.course)
        if cur_sem not in by_term:
            result = Result.objects.filter(
                student=student, semester=fg.semester, is_published=True,
            ).first()
            by_term[cur_sem] = {
                'semester_id': cur_sem,
                'curriculum_semester': cur_sem,
                'semester_name': format_curriculum_semester(cur_sem),
                'semester_label': format_curriculum_semester(cur_sem),
                'sgpa': str(result.sgpa) if result else None,
                'result_status': result.status if result else None,
                'courses': [],
            }
        by_term[cur_sem]['courses'].append({
            'course_code': fg.course.course_code,
            'course_name': fg.course.course_name,
            'credit_hours': fg.course.credit_hours,
            'grade_letter': fg.grade.grade_letter if fg.grade_id else '—',
            'grade_points': str(fg.grade.grade_points) if fg.grade_id else '—',
            'percentage': str(fg.percentage),
            'status': fg.status,
        })

    results = Result.objects.filter(
        student=student, is_published=True,
    ).select_related('semester').order_by('semester__academic_year', 'semester__start_date')

    return {
        'student': {
            'registration_number': student.registration_number,
            'name': student.user.username,
            'email': student.user.email,
            'program_name': student.program.program_name,
            'program_code': student.program.program_code,
            'batch_year': student.batch_year,
            'admission_date': str(student.admission_date),
            'graduation_date': str(student.graduation_date) if student.graduation_date else None,
            'status': student.status,
            'cgpa': str(student.cgpa),
        },
        'audit_summary': {
            'degree_completion_percent': audit['degree_completion_percent'],
            'earned_credit_hours': audit['earned_credit_hours'],
            'total_credit_hours': audit['total_credit_hours'],
            'eligible_for_graduation': audit['eligible'],
        },
        'semesters': [by_term[k] for k in sorted(by_term.keys())],
        'published_results': [
            {
                'semester_name': _result_semester_label(r),
                'sgpa': str(r.sgpa),
                'cgpa': str(r.cgpa),
                'status': r.status,
            }
            for r in results
        ],
        'cumulative_cgpa': str(student.cgpa),
        'issued_at': timezone.now().date().isoformat(),
        'document_type': 'official_transcript' if student.status == 'graduated' else 'unofficial_transcript',
    }
