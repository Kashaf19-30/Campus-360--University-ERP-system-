from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0003_courseprerequisite'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramCoursePrerequisite',
            fields=[
                ('prerequisite_id', models.AutoField(primary_key=True, serialize=False)),
                ('min_credit_hours', models.IntegerField(blank=True, null=True)),
                ('or_group', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='program_prerequisites', to='academics.course')),
                ('prerequisite_course', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='required_for_program_courses', to='academics.course')),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='course_prerequisites', to='academics.degreeprogram')),
            ],
            options={'db_table': 'program_course_prerequisite'},
        ),
    ]
