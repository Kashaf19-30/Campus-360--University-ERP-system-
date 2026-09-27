"""Reconcile carry-over failed courses as repeat registrations."""
from django.db import migrations


def reconcile_repeat_registrations(apps, schema_editor):
    CourseRegistration = apps.get_model('enrollments', 'CourseRegistration')
    FinalGrade = apps.get_model('examinations', 'FinalGrade')
    ProgramCourse = apps.get_model('academics', 'ProgramCourse')

    def is_regular(student, course_id):
        sem = ProgramCourse.objects.filter(
            program_id=student.program_id,
            course_id=course_id,
            semester_number=student.current_semester,
        ).exists()
        return sem

    for reg in CourseRegistration.objects.filter(status='registered').select_related('student'):
        fg = FinalGrade.objects.filter(registration_id=reg.registration_id, status='fail').first()
        should_repeat = bool(fg) or (
            reg.registration_type == 'regular' and not is_regular(reg.student, reg.course_id)
        )
        if should_repeat and reg.registration_type != 'repeat':
            reg.registration_type = 'repeat'
            reg.save(update_fields=['registration_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('enrollments', '0007_remove_carry_forward'),
        ('examinations', '0012_recompute_weighted_final_grades'),
    ]

    operations = [
        migrations.RunPython(reconcile_repeat_registrations, migrations.RunPython.noop),
    ]
