from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('examinations', '0009_cleanup_workflow_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='promotion_applied',
            field=models.BooleanField(default=False),
        ),
    ]
