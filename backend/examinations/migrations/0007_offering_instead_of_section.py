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


def migrate_exam_fks(apps, schema_editor):
    Examination = apps.get_model('examinations', 'Examination')
    MarksEditPermission = apps.get_model('examinations', 'MarksEditPermission')

    for row in Examination.objects.all():
        oid = _offering_id_for_section(apps, row.section_id)
        if oid:
            row.offering_id = oid
            row.save(update_fields=['offering_id'])

    for row in MarksEditPermission.objects.all():
        oid = _offering_id_for_section(apps, row.section_id)
        if oid:
            row.offering_id = oid
            row.save(update_fields=['offering_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0008_migrate_sections_to_offerings'),
        ('examinations', '0006_alter_finalgrade_registration'),
    ]

    operations = [
        migrations.AddField(
            model_name='examination',
            name='offering',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='examinations',
                to='academics.courseoffering',
            ),
        ),
        migrations.AddField(
            model_name='markseditpermission',
            name='offering',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='marks_edit_permissions',
                to='academics.courseoffering',
            ),
        ),
        migrations.RunPython(migrate_exam_fks, migrations.RunPython.noop),
        migrations.RemoveField(model_name='examination', name='section'),
        migrations.RemoveField(model_name='markseditpermission', name='section'),
        migrations.AlterField(
            model_name='examination',
            name='offering',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='examinations',
                to='academics.courseoffering',
            ),
        ),
        migrations.AlterField(
            model_name='markseditpermission',
            name='offering',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='marks_edit_permissions',
                to='academics.courseoffering',
            ),
        ),
    ]
