"""Set mid-term total to 30 and final total to 40 (aligned with weightage)."""

from decimal import Decimal

from django.db import migrations


def _rescale_marks(Examination, Marks, exam, old_total, new_total, updates):
    if 'total_marks' not in updates or not old_total or new_total == old_total:
        return
    ratio = Decimal(str(new_total)) / Decimal(str(old_total))
    for mark in Marks.objects.filter(exam=exam, obtained_marks__isnull=False):
        mark.obtained_marks = round(Decimal(str(mark.obtained_marks)) * ratio, 2)
        mark.save(update_fields=['obtained_marks'])


def apply_mid_final_defaults(apps, schema_editor):
    Examination = apps.get_model('examinations', 'Examination')
    ExamType = apps.get_model('examinations', 'ExamType')
    Marks = apps.get_model('examinations', 'Marks')

    mid_type_ids = set(
        ExamType.objects.filter(marks_period='mid_term').values_list('exam_type_id', flat=True)
    )
    final_type_ids = set(
        ExamType.objects.filter(marks_period='final').values_list('exam_type_id', flat=True)
    )

    for exam in Examination.objects.select_related('exam_type').iterator():
        updates = {}
        if exam.exam_type_id in mid_type_ids or exam.assessment_category == 'mid_term':
            updates = {
                'assessment_category': 'mid_term',
                'weight_percentage': Decimal('30'),
                'total_marks': Decimal('30'),
                'passing_marks': Decimal('15'),
            }
        elif exam.exam_type_id in final_type_ids or exam.assessment_category == 'final':
            updates = {
                'assessment_category': 'final',
                'weight_percentage': Decimal('40'),
                'total_marks': Decimal('40'),
                'passing_marks': Decimal('20'),
            }
        if not updates:
            continue

        old_total = exam.total_marks
        new_total = updates['total_marks']
        _rescale_marks(Examination, Marks, exam, old_total, new_total, updates)
        for field, value in updates.items():
            setattr(exam, field, value)
        exam.save(update_fields=list(updates.keys()))


class Migration(migrations.Migration):

    dependencies = [
        ('examinations', '0010_result_promotion_applied'),
    ]

    operations = [
        migrations.RunPython(apply_mid_final_defaults, migrations.RunPython.noop),
    ]
