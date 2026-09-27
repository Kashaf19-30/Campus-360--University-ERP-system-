from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0001_initial'),
        ('academics', '0006_alter_programcourseprerequisite_or_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseOffering',
            fields=[
                ('offering_id', models.AutoField(primary_key=True, serialize=False)),
                ('offering_type', models.CharField(
                    choices=[
                        ('theory', 'Theory'),
                        ('lab', 'Lab'),
                        ('theory_lab_combined', 'Theory + Lab Combined'),
                    ],
                    default='theory', max_length=30,
                )),
                ('max_capacity', models.IntegerField(default=40)),
                ('enrolled_count', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('marks_locked', models.BooleanField(default=False)),
                ('marks_unlock_until', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offerings', to='academics.course',
                )),
                ('faculty', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='course_offerings', to='faculty.faculty',
                )),
                ('semester', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offerings', to='academics.semester',
                )),
            ],
            options={
                'db_table': 'course_offering',
                'unique_together': {('course', 'semester', 'faculty')},
            },
        ),
        migrations.CreateModel(
            name='CourseOfferingSchedule',
            fields=[
                ('schedule_id', models.AutoField(primary_key=True, serialize=False)),
                ('day_of_week', models.CharField(max_length=10)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('room_number', models.CharField(max_length=20)),
                ('building_name', models.CharField(blank=True, max_length=100)),
                ('schedule_type', models.CharField(default='lecture', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('offering', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='schedules', to='academics.courseoffering',
                )),
            ],
            options={
                'db_table': 'course_offering_schedule',
            },
        ),
    ]
