from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sections', '0002_batchsection'),
    ]

    operations = [
        migrations.AddField(
            model_name='section',
            name='marks_locked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='section',
            name='marks_unlock_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
