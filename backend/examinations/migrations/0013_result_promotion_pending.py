from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('examinations', '0012_recompute_weighted_final_grades'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='promotion_pending',
            field=models.BooleanField(
                default=False,
                help_text='Admin approved promotion; awaiting target semester fee payment.',
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='pending_promotion_semester',
            field=models.IntegerField(
                blank=True,
                help_text='Curriculum semester number student will move to once fee is paid.',
                null=True,
            ),
        ),
    ]
