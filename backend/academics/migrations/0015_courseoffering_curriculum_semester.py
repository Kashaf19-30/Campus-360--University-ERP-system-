"""Add curriculum semester to course offerings."""
from django.db import migrations, models


def backfill_offering_curriculum_semester(apps, schema_editor):
    CourseOffering = apps.get_model('academics', 'CourseOffering')
    ProgramCourse = apps.get_model('academics', 'ProgramCourse')
    for offering in CourseOffering.objects.all().iterator():
        sem = ProgramCourse.objects.filter(
            course_id=offering.course_id,
        ).order_by('semester_number').values_list('semester_number', flat=True).first()
        offering.curriculum_semester = sem or 1
        offering.save(update_fields=['curriculum_semester'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0014_remove_carry_forward'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='curriculum_semester',
            field=models.IntegerField(
                default=1,
                help_text='Program curriculum semester this offering serves (user-facing semester number).',
            ),
        ),
        migrations.RunPython(backfill_offering_curriculum_semester, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='courseoffering',
            unique_together={('course', 'semester', 'faculty', 'curriculum_semester')},
        ),
    ]
