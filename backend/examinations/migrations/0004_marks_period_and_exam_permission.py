from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('examinations', '0003_markseditpermission_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='examtype',
            name='marks_period',
            field=models.CharField(
                choices=[
                    ('pre_mid', 'Pre Mid (A1, A2, Q1)'),
                    ('mid_term', 'Mid Term'),
                    ('post_mid', 'Post Mid (A3, Q2)'),
                    ('final', 'Final Term'),
                ],
                default='pre_mid',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='markseditpermission',
            name='examination',
            field=models.ForeignKey(
                blank=True,
                help_text='Specific exam this approval applies to',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='edit_permissions',
                to='examinations.examination',
            ),
        ),
    ]
