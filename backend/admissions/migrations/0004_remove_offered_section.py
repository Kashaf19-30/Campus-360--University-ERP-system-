from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0003_challan_rejected_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='admissiondecision',
            name='offered_section',
        ),
    ]
