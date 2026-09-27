# Generated migration for AcademicPolicy

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0009_alter_courseofferingschedule_day_of_week_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicPolicy',
            fields=[
                ('policy_id', models.AutoField(primary_key=True, serialize=False)),
                ('min_sgpa_pass', models.DecimalField(decimal_places=2, default=Decimal('2.0'), help_text='Minimum SGPA to pass a semester when no courses failed.', max_digits=3)),
                ('min_sgpa_probation', models.DecimalField(decimal_places=2, default=Decimal('2.0'), help_text='If courses failed but SGPA >= this, status is probation instead of fail.', max_digits=3)),
                ('min_cgpa_graduation', models.DecimalField(decimal_places=2, default=Decimal('2.0'), help_text='Minimum CGPA required to graduate.', max_digits=3)),
                ('max_consecutive_probation', models.IntegerField(default=2, help_text='Consecutive probation semesters before dismissal review is flagged.')),
                ('max_course_attempts', models.IntegerField(default=3, help_text='Maximum attempts allowed per course (future enforcement).')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'academic_policy',
            },
        ),
    ]
