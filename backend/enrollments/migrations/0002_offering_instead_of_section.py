from django.db import migrations, models
import django.db.models.deletion


def copy_section_to_offering(apps, schema_editor):
    Section = apps.get_model('sections', 'Section')
    CourseOffering = apps.get_model('academics', 'CourseOffering')
    CourseRegistration = apps.get_model('enrollments', 'CourseRegistration')

    for reg in CourseRegistration.objects.exclude(section_id__isnull=True):
        section = Section.objects.filter(section_id=reg.section_id).first()
        if not section:
            continue
        offering = CourseOffering.objects.filter(
            course_id=section.course_id,
            semester_id=section.semester_id,
            faculty_id=section.faculty_id,
        ).first()
        if offering:
            reg.offering_id = offering.offering_id
            reg.save(update_fields=['offering_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0008_migrate_sections_to_offerings'),
        ('enrollments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseregistration',
            name='offering',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='registrations',
                to='academics.courseoffering',
            ),
        ),
        migrations.RunPython(copy_section_to_offering, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='courseregistration',
            name='section',
        ),
        migrations.AlterField(
            model_name='courseregistration',
            name='offering',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='registrations',
                to='academics.courseoffering',
            ),
        ),
    ]
