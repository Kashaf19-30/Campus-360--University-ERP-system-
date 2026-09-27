from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sections', '0002_batchsection'),
        ('students', '0002_student_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='batch_section',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='students',
                to='sections.batchsection',
            ),
        ),
    ]
