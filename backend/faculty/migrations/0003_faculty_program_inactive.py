from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0002_initial'),
        ('faculty', '0002_faculty_profile_completed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faculty',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', 'Active'),
                    ('inactive', 'Inactive'),
                    ('on_leave', 'On Leave'),
                    ('resigned', 'Resigned'),
                    ('retired', 'Retired'),
                ],
                default='active',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='faculty',
            name='program',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='faculty_members',
                to='academics.degreeprogram',
            ),
        ),
    ]
