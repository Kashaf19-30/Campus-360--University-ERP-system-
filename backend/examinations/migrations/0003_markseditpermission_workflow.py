from django.db import migrations, models
import django.db.models.deletion


def remove_null_student_permissions(apps, schema_editor):
    MarksEditPermission = apps.get_model('examinations', 'MarksEditPermission')
    MarksEditPermission.objects.filter(student__isnull=True).delete()


def approve_existing_permissions(apps, schema_editor):
    MarksEditPermission = apps.get_model('examinations', 'MarksEditPermission')
    MarksEditPermission.objects.all().update(request_status='approved', is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('examinations', '0002_marks_edit_permission'),
        ('students', '0002_student_section'),
    ]

    operations = [
        migrations.RunPython(remove_null_student_permissions, migrations.RunPython.noop),
        migrations.AddField(
            model_name='markseditpermission',
            name='request_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                default='approved', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='markseditpermission',
            name='review_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='markseditpermission',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='markseditpermission',
            name='student',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='marks_edit_permissions',
                to='students.student',
            ),
        ),
        migrations.RunPython(approve_existing_permissions, migrations.RunPython.noop),
    ]
