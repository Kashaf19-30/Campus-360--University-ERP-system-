"""Auto-generate standard semester assessments from ExamType policy templates."""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from academics.models import CourseOffering, Semester
from .models import ExamType, Examination

_CATEGORY_BY_PERIOD = {
    'pre_mid': None,
    'mid_term': 'mid_term',
    'post_mid': None,
    'final': 'final',
}

CONTINUOUS_CATEGORIES = ('quiz', 'assignment', 'presentation')
REQUIRED_TOTAL_WEIGHT = Decimal('100')
FIXED_MID_WEIGHT = Decimal('30')
FIXED_FINAL_WEIGHT = Decimal('40')
FIXED_MID_TOTAL_MARKS = Decimal('30')
FIXED_FINAL_TOTAL_MARKS = Decimal('40')
FIXED_MID_PASSING_MARKS = Decimal('15')
FIXED_FINAL_PASSING_MARKS = Decimal('20')


def _exam_date_for_period(semester: Semester, period: str):
    start = semester.start_date
    end = semester.end_date
    mid = semester.mid_term_cutoff_date or (start + timedelta(days=56))
    if period == 'pre_mid':
        return start + timedelta(days=21)
    if period == 'mid_term':
        return mid
    if period == 'post_mid':
        return mid + timedelta(days=28)
    if period == 'final':
        return end - timedelta(days=7)
    return start + timedelta(days=14)


def _defaults_for_exam_type(exam_type: ExamType, semester: Semester) -> dict:
    period = exam_type.marks_period or 'pre_mid'
    category = _CATEGORY_BY_PERIOD.get(period)
    if period == 'pre_mid':
        return None
    if period == 'mid_term':
        return {
            'exam_name': exam_type.type_name,
            'exam_date': _exam_date_for_period(semester, period),
            'assessment_category': category,
            'total_marks': FIXED_MID_TOTAL_MARKS,
            'passing_marks': FIXED_MID_PASSING_MARKS,
            'weight_percentage': FIXED_MID_WEIGHT,
        }
    if period == 'final':
        return {
            'exam_name': exam_type.type_name,
            'exam_date': _exam_date_for_period(semester, period),
            'assessment_category': category,
            'total_marks': FIXED_FINAL_TOTAL_MARKS,
            'passing_marks': FIXED_FINAL_PASSING_MARKS,
            'weight_percentage': FIXED_FINAL_WEIGHT,
        }
    return {
        'exam_name': exam_type.type_name,
        'exam_date': _exam_date_for_period(semester, period),
        'assessment_category': category,
        'total_marks': Decimal('100'),
        'passing_marks': Decimal('50'),
        'weight_percentage': exam_type.weightage_percentage,
    }


def ensure_offering_assessments(offering, created_by=None) -> dict:
    """Create Mid (30%) and Final (40%) assessments if missing."""
    exam_types = list(
        ExamType.objects.filter(marks_period__in=['mid_term', 'final']).order_by('exam_type_id')
    )
    if not exam_types:
        return {'created': 0, 'skipped': 0, 'error': 'No exam types configured. Run seed_erp_data.'}

    existing_type_ids = set(
        Examination.objects.filter(offering=offering).values_list('exam_type_id', flat=True)
    )
    created = 0
    skipped = 0

    for exam_type in exam_types:
        if exam_type.exam_type_id in existing_type_ids:
            skipped += 1
            continue
        cfg = _defaults_for_exam_type(exam_type, offering.semester)
        if not cfg:
            continue
        Examination.objects.create(
            course=offering.course,
            semester=offering.semester,
            offering=offering,
            exam_type=exam_type,
            created_by=created_by,
            **cfg,
        )
        created += 1

    sync_mid_final_exam_defaults(offering)

    return {'created': created, 'skipped': skipped, 'offering_id': offering.offering_id}


def sync_mid_final_exam_defaults(offering) -> int:
    """Align mid (30) / final (40) totals, weights, passing marks; rescale marks if total changes."""
    from .marks_locking import resolve_marks_period, PERIOD_MID_TERM, PERIOD_FINAL
    from .models import Marks

    updated = 0
    for exam in Examination.objects.filter(offering=offering).select_related('exam_type'):
        period = resolve_marks_period(exam.exam_type)
        updates = {}
        if period == PERIOD_MID_TERM:
            if exam.assessment_category != 'mid_term':
                updates['assessment_category'] = 'mid_term'
            if exam.weight_percentage != FIXED_MID_WEIGHT:
                updates['weight_percentage'] = FIXED_MID_WEIGHT
            if exam.total_marks != FIXED_MID_TOTAL_MARKS:
                updates['total_marks'] = FIXED_MID_TOTAL_MARKS
            if exam.passing_marks != FIXED_MID_PASSING_MARKS:
                updates['passing_marks'] = FIXED_MID_PASSING_MARKS
        elif period == PERIOD_FINAL:
            if exam.assessment_category != 'final':
                updates['assessment_category'] = 'final'
            if exam.weight_percentage != FIXED_FINAL_WEIGHT:
                updates['weight_percentage'] = FIXED_FINAL_WEIGHT
            if exam.total_marks != FIXED_FINAL_TOTAL_MARKS:
                updates['total_marks'] = FIXED_FINAL_TOTAL_MARKS
            if exam.passing_marks != FIXED_FINAL_PASSING_MARKS:
                updates['passing_marks'] = FIXED_FINAL_PASSING_MARKS
        if not updates:
            continue

        old_total = exam.total_marks
        new_total = updates.get('total_marks', old_total)
        if 'total_marks' in updates and old_total and new_total != old_total:
            ratio = Decimal(str(new_total)) / Decimal(str(old_total))
            for mark in Marks.objects.filter(exam=exam, obtained_marks__isnull=False):
                mark.obtained_marks = round(Decimal(str(mark.obtained_marks)) * ratio, 2)
                mark.save(update_fields=['obtained_marks'])

        for field, value in updates.items():
            setattr(exam, field, value)
        exam.save(update_fields=list(updates.keys()))
        updated += 1
    return updated


@transaction.atomic
def initialize_semester_assessments(semester_id, created_by=None) -> dict:
    try:
        semester = Semester.objects.get(semester_id=semester_id)
    except Semester.DoesNotExist:
        return {'error': 'Semester not found.'}

    offerings = CourseOffering.objects.filter(
        semester=semester, is_active=True,
    ).select_related('course', 'semester')

    total_created = 0
    total_skipped = 0
    offerings_processed = 0
    offerings_complete = 0
    exam_type_count = ExamType.objects.filter(marks_period__in=['mid_term', 'final']).count()

    for offering in offerings:
        result = ensure_offering_assessments(offering, created_by=created_by)
        total_created += result['created']
        total_skipped += result['skipped']
        offerings_processed += 1
        exam_count = Examination.objects.filter(
            offering=offering, assessment_category__in=['mid_term', 'final'],
        ).count()
        if exam_type_count and exam_count >= exam_type_count:
            offerings_complete += 1

    return {
        'semester_id': semester.semester_id,
        'semester_name': semester.semester_name,
        'offerings_processed': offerings_processed,
        'offerings_complete': offerings_complete,
        'exams_created': total_created,
        'exams_skipped': total_skipped,
        'expected_per_offering': exam_type_count,
    }


def get_semester_assessment_status(semester_id) -> dict:
    try:
        semester = Semester.objects.get(semester_id=semester_id)
    except Semester.DoesNotExist:
        return {'error': 'Semester not found.'}

    exam_type_count = ExamType.objects.filter(marks_period__in=['mid_term', 'final']).count()
    offerings = CourseOffering.objects.filter(
        semester=semester, is_active=True,
    ).select_related('course', 'faculty__user')

    offering_rows = []
    ready = 0
    awaiting_marks = 0
    locked = 0

    for off in offerings:
        exam_count = Examination.objects.filter(
            offering=off, assessment_category__in=['mid_term', 'final'],
        ).count()
        complete = exam_type_count > 0 and exam_count >= exam_type_count
        if complete:
            ready += 1
        if off.marks_locked:
            locked += 1
        elif complete:
            awaiting_marks += 1
        offering_rows.append({
            'offering_id': off.offering_id,
            'course_code': off.course.course_code,
            'course_name': off.course.course_name,
            'faculty_name': off.faculty.user.username if off.faculty_id else '—',
            'exam_count': exam_count,
            'expected_exams': exam_type_count,
            'assessments_ready': complete,
            'marks_locked': off.marks_locked,
            'enrolled_count': off.enrolled_count,
        })

    total_offerings = offerings.count()
    return {
        'semester_id': semester.semester_id,
        'semester_name': semester.semester_name,
        'total_offerings': total_offerings,
        'offerings_with_assessments': ready,
        'offerings_missing_assessments': max(0, total_offerings - ready),
        'awaiting_marks': awaiting_marks,
        'marks_locked': locked,
        'expected_exams_per_offering': exam_type_count,
        'offerings': offering_rows,
    }


def resolve_exam_weight_percentage(exam) -> Decimal:
    """Course weight % for an exam (mid=30, final=40, CA uses exam.weight_percentage)."""
    if exam.assessment_category == 'mid_term':
        return FIXED_MID_WEIGHT
    if exam.assessment_category == 'final':
        return FIXED_FINAL_WEIGHT
    if exam.weight_percentage is not None:
        return Decimal(str(exam.weight_percentage))
    if exam.exam_type_id and exam.exam_type.weightage_percentage is not None:
        return Decimal(str(exam.exam_type.weightage_percentage))
    return Decimal('0')


def compute_weighted_mark_points(obtained_marks, total_marks, weight_percentage, *, is_absent=False):
    """
    Course contribution points (out of weight_percentage toward course total 100).
    e.g. mid 15/30 at 30% → 15.00 / 30.00; quiz 5/10 at 10% → 5.00 / 10.00
    """
    if is_absent or obtained_marks is None or not total_marks:
        return None, None
    obtained = Decimal(str(obtained_marks))
    total = Decimal(str(total_marks))
    weight = Decimal(str(weight_percentage))
    if total <= 0:
        return None, None
    points = round((obtained / total) * weight, 2)
    max_pts = round(weight, 2)
    return points, max_pts


def get_promotion_relevant_examinations(offering):
    """Assessments included in the 100% course weight structure."""
    from django.db.models import Q

    return Examination.objects.filter(offering=offering).filter(
        Q(assessment_category__in=['mid_term', 'final'])
        | Q(
            assessment_category__in=CONTINUOUS_CATEGORIES,
            weight_percentage__isnull=False,
            weight_percentage__gt=0,
        )
    )


def get_offering_weight_allocation_status(offering) -> dict:
    """Whether teacher allocated the full 100% (30 continuous + 30 mid + 40 final)."""
    exams = Examination.objects.filter(offering=offering)
    continuous_used = Decimal('0')
    for cat in CONTINUOUS_CATEGORIES:
        for exam in exams.filter(assessment_category=cat):
            if exam.weight_percentage is not None:
                continuous_used += Decimal(str(exam.weight_percentage))

    mid_w = Decimal('0')
    final_w = Decimal('0')
    has_mid = exams.filter(assessment_category='mid_term').exists()
    has_final = exams.filter(assessment_category='final').exists()
    mid_exam = exams.filter(assessment_category='mid_term').first()
    final_exam = exams.filter(assessment_category='final').first()
    if mid_exam and mid_exam.weight_percentage is not None:
        mid_w = Decimal(str(mid_exam.weight_percentage))
    if final_exam and final_exam.weight_percentage is not None:
        final_w = Decimal(str(final_exam.weight_percentage))

    total = continuous_used + mid_w + final_w
    weight_complete = (
        has_mid
        and has_final
        and total == REQUIRED_TOTAL_WEIGHT
        and mid_w == FIXED_MID_WEIGHT
        and final_w == FIXED_FINAL_WEIGHT
    )
    return {
        'total_allocated': float(total),
        'required_total': float(REQUIRED_TOTAL_WEIGHT),
        'continuous_allocated': float(continuous_used),
        'continuous_required': 30.0,
        'mid_allocated': float(mid_w),
        'final_allocated': float(final_w),
        'has_mid_term': has_mid,
        'has_final_term': has_final,
        'weight_complete': weight_complete,
    }
