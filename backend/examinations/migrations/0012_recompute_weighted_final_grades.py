"""Recompute course grades using weighted points (not raw paper marks)."""

from django.db import migrations


def recompute_final_grades(apps, schema_editor):
    from examinations.results_pipeline import recompute_all_final_grades
    recompute_all_final_grades()


class Migration(migrations.Migration):

    dependencies = [
        ('examinations', '0011_mid_final_default_totals'),
    ]

    operations = [
        migrations.RunPython(recompute_final_grades, migrations.RunPython.noop),
    ]
