from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0007_gap_fixes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicant',
            name='cnic',
            field=models.CharField(blank=True, max_length=13, null=True),
        ),
    ]
