from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_alter_student_section'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='student',
            name='batch_section',
        ),
        migrations.RemoveField(
            model_name='student',
            name='section',
        ),
    ]
