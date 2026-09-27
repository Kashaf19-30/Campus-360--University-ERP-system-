from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0007_student_academic_standing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='graduation_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
