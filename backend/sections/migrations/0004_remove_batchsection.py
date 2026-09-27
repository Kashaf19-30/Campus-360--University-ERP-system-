from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sections', '0003_section_marks_locking'),
        ('students', '0006_remove_student_batch_section_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BatchSection',
        ),
    ]
