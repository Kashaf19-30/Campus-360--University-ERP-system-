"""
Semester result aggregation and publication helpers.
"""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from examinations.models import FinalGrade, Grade, Marks, Result
from enrollments.models import Enrollment, CourseRegistration


def grade_for_percentage(pct: Decimal):
    grades = Grade.objects.all().order_by('-min_percentage')
    if not grades.exists():
        return None
    for g in grades:
        if pct >= g.min_percentage:
            return g
    return grades.order_by('min_percentage').first()


def compute_offering_final_grades(offering) -> dict:
    """
    Build FinalGrade rows from weighted assessment points (out of 100% course weight).
    total_obtained_marks / total_marks store course points, not raw paper marks.
    """
    from examinations.assessment_setup import (
        get_promotion_relevant_examinations,
        resolve_exam_weight_percentage,
        compute_weighted_mark_points,
    )

    from enrollments.repeat_utils import roster_eligible_registrations

    exams = list(get_promotion_relevant_examinations(offering).select_related('exam_type'))
    if not exams:
        return {'created': 0, 'updated': 0}

    regs = roster_eligible_registrations(offering).select_related('student')
    created, updated = 0, 0

    for reg in regs:
        total_obtained = Decimal('0')
        total_possible = Decimal('0')
        for exam in exams:
            weight = resolve_exam_weight_percentage(exam)
            total_possible += weight
            mark = Marks.objects.filter(exam=exam, student=reg.student).first()
            if mark and not mark.is_absent and mark.obtained_marks is not None:
                pts, _ = compute_weighted_mark_points(
                    mark.obtained_marks, exam.total_marks, weight,
                )
                if pts is not None:
                    total_obtained += pts

        if total_possible <= 0:
            continue

        percentage = (total_obtained / total_possible) * Decimal('100')
        grade_obj = grade_for_percentage(percentage)
        if grade_obj is None:
            continue
        status_val = grade_obj.status

        fg, was_created = FinalGrade.objects.update_or_create(
            registration=reg,
            defaults={
                'student': reg.student,
                'course': offering.course,
                'semester': offering.semester,
                'total_obtained_marks': total_obtained,
                'total_marks': total_possible,
                'percentage': percentage,
                'grade': grade_obj,
                'status': status_val,
            },
        )
        sync_registration_from_final_grade(fg)
        if was_created:
            created += 1
        else:
            updated += 1

    return {'created': created, 'updated': updated}


def recompute_all_final_grades() -> dict:
    """Recalculate every FinalGrade from current marks using weighted points."""
    from academics.models import CourseOffering, Semester

    offering_ids = set(
        FinalGrade.objects.filter(registration__offering_id__isnull=False)
        .values_list('registration__offering_id', flat=True)
    )
    offerings_updated = 0
    for offering in CourseOffering.objects.filter(offering_id__in=offering_ids):
        compute_offering_final_grades(offering)
        offerings_updated += 1

    semester_ids = set(FinalGrade.objects.values_list('semester_id', flat=True))
    results_updated = 0
    for semester in Semester.objects.filter(semester_id__in=semester_ids):
        stats = generate_results_for_semester(semester)
        results_updated += stats.get('results_created_or_updated', 0)

    return {'offerings_updated': offerings_updated, 'results_updated': results_updated}


def _grade_points_for(grade_obj) -> Decimal:
    return grade_obj.grade_points if grade_obj else Decimal('0')


def sync_registration_from_final_grade(final_grade: FinalGrade) -> None:
    """Keep CourseRegistration grade_points/status aligned with FinalGrade."""
    reg = final_grade.registration
    reg.grade_points = _grade_points_for(final_grade.grade)
    update_fields = ['grade_points', 'status']
    if final_grade.status == 'pass':
        reg.status = 'completed'
    elif final_grade.status == 'fail':
        reg.status = 'registered'
        if reg.registration_type != 'repeat':
            reg.registration_type = 'repeat'
            update_fields.append('registration_type')
    reg.save(update_fields=update_fields)


def compute_student_sgpa(student, semester) -> dict:
    """Compute SGPA from FinalGrade rows for a student in a semester."""
    from academics.policy_utils import get_academic_policy, semester_status_from_sgpa

    policy = get_academic_policy()
    grades = FinalGrade.objects.filter(
        student=student, semester=semester,
    ).select_related('registration__course', 'grade')

    attempted_ch = 0
    earned_ch = 0
    weighted_points = Decimal('0')
    fail_count = 0

    for fg in grades:
        ch = fg.course.credit_hours
        attempted_ch += ch
        gp = _grade_points_for(fg.grade)
        weighted_points += gp * ch
        if fg.status == 'pass':
            earned_ch += ch
        else:
            fail_count += 1

    sgpa = (weighted_points / attempted_ch) if attempted_ch else Decimal('0')
    status = semester_status_from_sgpa(sgpa, fail_count, policy)

    return {
        'sgpa': round(sgpa, 2),
        'attempted_ch': attempted_ch,
        'earned_ch': earned_ch,
        'status': status,
        'fail_count': fail_count,
    }


def effective_final_grades_for_cgpa(student):
    """
    One effective grade per course for cumulative GPA.
    Uses the best grade points across attempts (pass on repeat replaces earlier fail).
    Failed courses count with 0 points until a better attempt exists.
    """
    best = {}
    for fg in FinalGrade.objects.filter(student=student).select_related('course', 'grade'):
        cid = fg.course_id
        gp = _grade_points_for(fg.grade)
        if cid not in best or gp > best[cid]['gp']:
            best[cid] = {'gp': gp, 'ch': fg.course.credit_hours, 'fg': fg}
    return [entry['fg'] for entry in best.values()]


def compute_student_cgpa(student) -> Decimal:
    """Cumulative GPA — all courses counted once using best attempt per course."""
    grades = effective_final_grades_for_cgpa(student)
    total_points = Decimal('0')
    total_ch = 0
    for fg in grades:
        ch = fg.course.credit_hours
        total_ch += ch
        total_points += _grade_points_for(fg.grade) * ch
    if not total_ch:
        return Decimal('0')
    return round(total_points / total_ch, 2)


def compute_student_earned_credit_hours(student) -> int:
    """Credit hours earned using best attempt per course."""
    return sum(
        fg.course.credit_hours
        for fg in effective_final_grades_for_cgpa(student)
        if fg.status == 'pass'
    )


def refresh_student_academic_record(student) -> list:
    """
    Recompute SGPA/CGPA for every semester result and sync student profile.
    Call after final marks submission (especially repeat/improvement attempts).
    """
    from academics.models import Semester
    from students.models import Student

    if isinstance(student, int):
        student = Student.objects.get(pk=student)

    cgpa = compute_student_cgpa(student)
    earned_ch = compute_student_earned_credit_hours(student)

    semester_ids = FinalGrade.objects.filter(
        student=student,
    ).values_list('semester_id', flat=True).distinct()

    updated_results = []
    for sem_id in semester_ids:
        semester = Semester.objects.get(pk=sem_id)
        updated_results.append(ensure_semester_result(student, semester))

    student.cgpa = cgpa
    student.total_credit_hours_completed = earned_ch
    student.save(update_fields=['cgpa', 'total_credit_hours_completed'])

    Result.objects.filter(student=student).update(cgpa=cgpa)

    return updated_results


def refresh_students_after_offering_grades(offering) -> dict:
    """Recalculate academic records for every student graded on this offering."""
    student_ids = set(
        CourseRegistration.objects.filter(
            offering=offering,
            status__in=['registered', 'completed'],
        ).values_list('student_id', flat=True)
    )

    from students.models import Student

    refreshed = []
    for sid in student_ids:
        student = Student.objects.get(pk=sid)
        results = refresh_student_academic_record(student)
        refreshed.append({
            'student_id': sid,
            'registration_number': student.registration_number,
            'cgpa': str(student.cgpa),
            'semesters_updated': len(results),
        })

    return {'students_refreshed': len(refreshed), 'students': refreshed}


def ensure_semester_result(student, semester, *, created_by=None) -> Result:
    """Create or update Result row from FinalGrade aggregation."""
    stats = compute_student_sgpa(student, semester)
    cgpa = compute_student_cgpa(student)

    result, _ = Result.objects.update_or_create(
        student=student,
        semester=semester,
        defaults={
            'sgpa': stats['sgpa'],
            'cgpa': cgpa,
            'total_credit_hours_attempted': stats['attempted_ch'],
            'total_credit_hours_earned': stats['earned_ch'],
            'status': stats['status'],
        },
    )

    student.cgpa = cgpa
    student.total_credit_hours_completed = compute_student_earned_credit_hours(student)
    student.save(update_fields=['cgpa', 'total_credit_hours_completed'])

    enrollment = Enrollment.objects.filter(student=student, semester=semester).first()
    if enrollment and stats['fail_count'] == 0:
        enrollment.status = 'completed'
        enrollment.save(update_fields=['status'])

    return result


def generate_results_for_semester(semester) -> dict:
    """Build Result rows for every student with FinalGrades in a semester."""
    student_ids = FinalGrade.objects.filter(
        semester=semester,
    ).values_list('student_id', flat=True).distinct()

    created = 0
    for sid in student_ids:
        from students.models import Student
        student = Student.objects.get(student_id=sid)
        ensure_semester_result(student, semester)
        created += 1
    return {'results_created_or_updated': created}


def published_semester_ids_for(student) -> set:
    return set(
        Result.objects.filter(student=student, is_published=True).values_list(
            'semester_id', flat=True
        )
    )
