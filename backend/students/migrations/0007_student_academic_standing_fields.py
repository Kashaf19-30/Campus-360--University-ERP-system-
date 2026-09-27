from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0006_remove_student_batch_section_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='consecutive_probation_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='student',
            name='academic_review_required',
            field=models.BooleanField(default=False),
        ),
    ]
