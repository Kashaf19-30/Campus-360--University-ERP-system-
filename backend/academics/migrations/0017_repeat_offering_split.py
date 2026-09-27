"""Separate repeat offerings from regular batch offerings."""
from django.db import migrations, models


def split_repeat_offerings(apps, schema_editor):
    CourseOffering = apps.get_model('academics', 'CourseOffering')
    CourseRegistration = apps.get_model('enrollments', 'CourseRegistration')
    Examination = apps.get_model('examinations', 'Examination')

    for reg in CourseRegistration.objects.filter(
        registration_type__in=['repeat', 'prerequisite_repeat'],
        status='registered',
    ).select_related('offering', 'course', 'student'):
        old = reg.offering
        if not old:
            continue
        repeat_offering, _ = CourseOffering.objects.get_or_create(
            course_id=old.course_id,
            semester_id=old.semester_id,
            faculty_id=old.faculty_id,
            curriculum_semester=old.curriculum_semester,
            repeat_offering=True,
            defaults={
                'offering_type': old.offering_type,
                'is_active': True,
                'marks_locked': False,
            },
        )
        if reg.offering_id != repeat_offering.offering_id:
            reg.offering_id = repeat_offering.offering_id
            reg.save(update_fields=['offering_id'])

    for offering in CourseOffering.objects.all():
        actual = CourseRegistration.objects.filter(
            offering=offering, status='registered',
        ).count()
        if offering.enrolled_count != actual:
            offering.enrolled_count = actual
            offering.save(update_fields=['enrolled_count'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0016_normalize_active_session'),
        ('enrollments', '0008_reconcile_repeat_registrations'),
        ('examinations', '0012_recompute_weighted_final_grades'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='repeat_offering',
            field=models.BooleanField(
                default=False,
                help_text='True = repeat/improvement section (separate from regular batch).',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='courseoffering',
            unique_together={('course', 'semester', 'faculty', 'curriculum_semester', 'repeat_offering')},
        ),
        migrations.RunPython(split_repeat_offerings, migrations.RunPython.noop),
    ]
