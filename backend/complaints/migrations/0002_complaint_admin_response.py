# Generated migration for complaint admin_response

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('complaints', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='admin_response',
            field=models.TextField(blank=True),
        ),
    ]
