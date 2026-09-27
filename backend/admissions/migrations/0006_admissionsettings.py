from django.db import migrations, models


def seed_open_admissions(apps, schema_editor):
    AdmissionSettings = apps.get_model('admissions', 'AdmissionSettings')
    AdmissionSettings.objects.get_or_create(pk=1, defaults={'is_open': True})


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0005_alter_admissionlog_action_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdmissionSettings',
            fields=[
                ('settings_id', models.AutoField(primary_key=True, serialize=False)),
                ('is_open', models.BooleanField(default=True, help_text='When False, new applicants see Admission Closed after signup.')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'admission_settings',
            },
        ),
        migrations.RunPython(seed_open_admissions, migrations.RunPython.noop),
    ]
