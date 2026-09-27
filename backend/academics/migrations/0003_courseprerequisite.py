from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoursePrerequisite',
            fields=[
                ('prerequisite_id', models.AutoField(primary_key=True, serialize=False)),
                ('prerequisite_type', models.CharField(
                    choices=[('course', 'Course'), ('credit_hours', 'Minimum Credit Hours')],
                    default='course', max_length=20,
                )),
                ('min_credit_hours', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='prerequisites', to='academics.course',
                )),
                ('prerequisite_course', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='required_for_courses', to='academics.course',
                )),
            ],
            options={
                'db_table': 'course_prerequisite',
                'unique_together': {
                    ('course', 'prerequisite_type', 'prerequisite_course'),
                    ('course', 'prerequisite_type', 'min_credit_hours'),
                },
            },
        ),
    ]
