from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0002_faculty_profile_completed'),
        ('sections', '0003_section_marks_locking'),
        ('students', '0002_student_section'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('examinations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarksEditPermission',
            fields=[
                ('permission_id', models.AutoField(primary_key=True, serialize=False)),
                ('expires_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('granted_by', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, related_name='granted_marks_permissions', to=settings.AUTH_USER_MODEL)),
                ('granted_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marks_edit_permissions', to='faculty.faculty')),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marks_edit_permissions', to='sections.section')),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='marks_edit_permissions', to='students.student')),
            ],
            options={
                'db_table': 'marks_edit_permission',
            },
        ),
    ]
