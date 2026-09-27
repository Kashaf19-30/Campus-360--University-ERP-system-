from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0003_faculty_program_inactive'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faculty',
            name='employment_type',
            field=models.CharField(
                choices=[
                    ('permanent', 'Permanent'),
                    ('visiting', 'Visiting'),
                    ('contract', 'Contract'),
                    ('contractual', 'Contractual'),
                ],
                max_length=30,
            ),
        ),
    ]
