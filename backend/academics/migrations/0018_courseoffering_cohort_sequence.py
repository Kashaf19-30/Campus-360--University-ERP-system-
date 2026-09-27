"""Allow multiple regular offerings per session when a new curriculum cohort starts."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0017_repeat_offering_split'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoffering',
            name='cohort_sequence',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Intake/class sequence when the same course+session+teacher is taught again to a new cohort.',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='courseoffering',
            unique_together={
                ('course', 'semester', 'faculty', 'curriculum_semester', 'repeat_offering', 'cohort_sequence'),
            },
        ),
    ]
