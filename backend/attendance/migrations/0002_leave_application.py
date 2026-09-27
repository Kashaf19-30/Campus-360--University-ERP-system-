from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_student_section'),
        ('sections', '0003_section_marks_locking'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LeaveApplication',
            fields=[
                ('leave_id', models.AutoField(primary_key=True, serialize=False)),
                ('reason', models.TextField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('teacher_remarks', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_leaves', to=settings.AUTH_USER_MODEL)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_applications', to='sections.section')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_applications', to='students.student')),
            ],
            options={
                'db_table': 'leave_application',
            },
        ),
    ]
