from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0002_admission_challan_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='admissionapplication',
            name='challan_rejected_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Deadline anchor for re-upload after OCR/admin rejection',
                null=True,
            ),
        ),
    ]
