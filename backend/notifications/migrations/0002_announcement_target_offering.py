from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0014_remove_carry_forward'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcement',
            name='target_offering',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='announcements',
                to='academics.courseoffering',
            ),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='target_audience',
            field=models.CharField(
                choices=[
                    ('all', 'All'),
                    ('students', 'Students'),
                    ('faculty', 'Faculty'),
                    ('staff', 'Staff'),
                    ('specific_program', 'Specific Program'),
                    ('course_offering', 'Course Offering'),
                ],
                default='all',
                max_length=50,
            ),
        ),
    ]
