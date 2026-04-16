"""
Data migration: ensure ProductivitySettings.default_weight is 0.5.

If the row was manually set to 0.0 in the Django admin, all neutral /
uncategorized apps received weight 0.0 and were bucketed as NON_PRODUCTIVE,
causing 0% productive / 0% neutral on the dashboard even for apps whose
AppCategory shows "Neutral".
"""

from django.db import migrations


def fix_default_weight(apps, schema_editor):
    ProductivitySettings = apps.get_model('tracker_api', 'ProductivitySettings')
    obj, created = ProductivitySettings.objects.get_or_create(pk=1)
    if obj.default_weight <= 0.3:
        obj.default_weight = 0.5
        obj.save(update_fields=['default_weight'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker_api', '0012_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(fix_default_weight, migrations.RunPython.noop),
    ]
