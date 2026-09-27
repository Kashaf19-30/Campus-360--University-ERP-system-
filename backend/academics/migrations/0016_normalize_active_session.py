"""Use a single internal active session label (curriculum semester is user-facing)."""
from django.db import migrations


def normalize_active_session_names(apps, schema_editor):
    Semester = apps.get_model('academics', 'Semester')
    current = Semester.objects.filter(is_current=True).order_by('-semester_id').first()
    if current:
        current.semester_name = 'Active Session'
        current.save(update_fields=['semester_name'])
    for sem in Semester.objects.exclude(pk=current.pk if current else None):
        name = sem.semester_name or ''
        if name.startswith(('Spring ', 'Fall ', 'Summer ')):
            sem.semester_name = f'Legacy Session {sem.semester_id}'
            sem.is_current = False
            sem.save(update_fields=['semester_name', 'is_current'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0015_courseoffering_curriculum_semester'),
    ]

    operations = [
        migrations.RunPython(normalize_active_session_names, migrations.RunPython.noop),
    ]
