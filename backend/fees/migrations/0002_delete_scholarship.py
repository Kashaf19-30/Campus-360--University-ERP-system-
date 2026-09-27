from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Scholarship',
        ),
    ]
