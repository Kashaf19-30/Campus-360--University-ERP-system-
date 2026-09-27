from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_programcourseprerequisite'),
    ]

    operations = [
        migrations.AddField(
            model_name='semester',
            name='mid_term_cutoff_date',
            field=models.DateField(blank=True, help_text='After this, pre-mid + mid-term marks lock', null=True),
        ),
        migrations.AddField(
            model_name='semester',
            name='marks_grace_end_date',
            field=models.DateField(blank=True, help_text='Default: end_date + 7 days', null=True),
        ),
    ]
