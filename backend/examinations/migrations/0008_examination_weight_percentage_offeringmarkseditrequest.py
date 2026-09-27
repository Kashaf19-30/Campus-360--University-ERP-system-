# Generated manually for prototype demo

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('academics', '0010_academicpolicy'),
        ('faculty', '0006_facultycourseassignment'),
        ('examinations', '0007_offering_instead_of_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='examination',
            name='weight_percentage',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Share of final grade (e.g. 10 for 10%). Used for continuous sub-assessments.',
                max_digits=5,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name='OfferingMarksEditRequest',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('reason', models.TextField()),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                    default='pending',
                    max_length=20,
                )),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('admin_remarks', models.TextField(blank=True)),
                ('faculty', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offering_edit_requests',
                    to='faculty.faculty',
                )),
                ('offering', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='marks_edit_requests',
                    to='academics.courseoffering',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_offering_edit_requests',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'offering_marks_edit_request',
            },
        ),
    ]
