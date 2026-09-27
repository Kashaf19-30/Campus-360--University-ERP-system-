from django.db import migrations


def migrate_sections_to_offerings(apps, schema_editor):
    Section = apps.get_model('sections', 'Section')
    SectionSchedule = apps.get_model('sections', 'SectionSchedule')
    CourseOffering = apps.get_model('academics', 'CourseOffering')
    CourseOfferingSchedule = apps.get_model('academics', 'CourseOfferingSchedule')

    key_to_offering_id = {}

    for section in Section.objects.all().order_by('section_id'):
        key = (section.course_id, section.semester_id, section.faculty_id)
        if key in key_to_offering_id:
            continue
        offering = CourseOffering(
            offering_id=section.section_id,
            course_id=section.course_id,
            semester_id=section.semester_id,
            faculty_id=section.faculty_id,
            offering_type=section.section_type,
            max_capacity=section.max_capacity,
            enrolled_count=section.enrolled_count,
            is_active=section.is_active,
            marks_locked=getattr(section, 'marks_locked', False),
            marks_unlock_until=getattr(section, 'marks_unlock_until', None),
            created_at=section.created_at,
        )
        offering.save()
        key_to_offering_id[key] = section.section_id

    def offering_id_for_section(section_id):
        section = Section.objects.filter(section_id=section_id).first()
        if not section:
            return None
        key = (section.course_id, section.semester_id, section.faculty_id)
        return key_to_offering_id.get(key)

    for sched in SectionSchedule.objects.all():
        oid = offering_id_for_section(sched.section_id)
        if not oid:
            continue
        CourseOfferingSchedule.objects.create(
            offering_id=oid,
            day_of_week=sched.day_of_week,
            start_time=sched.start_time,
            end_time=sched.end_time,
            room_number=sched.room_number,
            building_name=sched.building_name,
            schedule_type=sched.schedule_type,
            created_at=sched.created_at,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0007_courseoffering'),
        ('sections', '0004_remove_batchsection'),
    ]

    operations = [
        migrations.RunPython(migrate_sections_to_offerings, noop),
    ]
