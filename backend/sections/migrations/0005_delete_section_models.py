from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sections', '0004_remove_batchsection'),
        ('enrollments', '0002_offering_instead_of_section'),
        ('attendance', '0003_offering_instead_of_section'),
        ('examinations', '0007_offering_instead_of_section'),
    ]

    operations = [
        migrations.DeleteModel(name='SectionSchedule'),
        migrations.DeleteModel(name='Section'),
    ]
