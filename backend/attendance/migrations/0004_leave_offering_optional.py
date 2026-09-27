from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0007_courseoffering'),
        ('attendance', '0003_offering_instead_of_section'),
    ]

    operations = [
        migrations.AlterField(
            model_name='leaveapplication',
            name='offering',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='leave_applications',
                to='academics.courseoffering',
            ),
        ),
    ]
