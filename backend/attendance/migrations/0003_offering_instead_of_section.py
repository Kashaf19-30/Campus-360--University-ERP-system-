from django.db import migrations, models
import django.db.models.deletion


def _offering_id_for_section(apps, section_id):
    if not section_id:
        return None
    Section = apps.get_model('sections', 'Section')
    CourseOffering = apps.get_model('academics', 'CourseOffering')
    section = Section.objects.filter(section_id=section_id).first()
    if not section:
        return None
    offering = CourseOffering.objects.filter(
        course_id=section.course_id,
        semester_id=section.semester_id,
        faculty_id=section.faculty_id,
    ).first()
    return offering.offering_id if offering else None


def migrate_attendance_fks(apps, schema_editor):
    Attendance = apps.get_model('attendance', 'Attendance')
    StudentAttendanceSummary = apps.get_model('attendance', 'StudentAttendanceSummary')
    LeaveApplication = apps.get_model('attendance', 'LeaveApplication')

    for row in Attendance.objects.all():
        oid = _offering_id_for_section(apps, row.section_id)
        if oid:
            row.offering_id = oid
            row.save(update_fields=['offering_id'])

    for row in StudentAttendanceSummary.objects.all():
        oid = _offering_id_for_section(apps, row.section_id)
        if oid:
            row.offering_id = oid
            row.save(update_fields=['offering_id'])

    for row in LeaveApplication.objects.all():
        oid = _offering_id_for_section(apps, row.section_id)
        if oid:
            row.offering_id = oid
            row.save(update_fields=['offering_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0008_migrate_sections_to_offerings'),
        ('attendance', '0002_leave_application'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='offering',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='attendances',
                to='academics.courseoffering',
            ),
        ),
        migrations.AddField(
            model_name='studentattendancesummary',
            name='offering',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='attendance_summaries',
                to='academics.courseoffering',
            ),
        ),
        migrations.AddField(
            model_name='leaveapplication',
            name='offering',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='leave_applications',
                to='academics.courseoffering',
            ),
        ),
        migrations.RunPython(migrate_attendance_fks, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together={('offering', 'attendance_date', 'lecture_number')},
        ),
        migrations.AlterUniqueTogether(
            name='studentattendancesummary',
            unique_together={('student', 'offering')},
        ),
        migrations.RemoveField(model_name='attendance', name='section'),
        migrations.RemoveField(model_name='studentattendancesummary', name='section'),
        migrations.RemoveField(model_name='leaveapplication', name='section'),
        migrations.AlterField(
            model_name='attendance',
            name='offering',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='attendances',
                to='academics.courseoffering',
            ),
        ),
        migrations.AlterField(
            model_name='studentattendancesummary',
            name='offering',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='attendance_summaries',
                to='academics.courseoffering',
            ),
        ),
        migrations.AlterField(
            model_name='leaveapplication',
            name='offering',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='leave_applications',
                to='academics.courseoffering',
            ),
        ),
    ]
