"""
Data migration: tighten productivity scoring defaults.

Changes:
  default_weight          0.5 → 0.3  (neutral/unknown apps count less)
  productive_threshold    70  → 75   (harder to be "productive")
  needs_improvement_threshold 50 → 60  (harder to stay out of "unproductive")

Rationale:
  - SPACE framework research shows deep-work IDEs should dominate the score.
  - With all neutral apps previously scored at 0.5, even heavy browser / messaging
    use produced inflated scores.  0.3 reflects that neutral intent is ambiguous.
  - Raising thresholds aligns with GitLab DevEx 2023 benchmarks where top
    quartile developers spend ~75 %+ of shift in high-value tools.
"""

from django.db import migrations


def update_defaults(apps, schema_editor):
    ProductivitySettings = apps.get_model('tracker_api', 'ProductivitySettings')
    obj, _ = ProductivitySettings.objects.get_or_create(pk=1)
    obj.default_weight = 0.3
    obj.productive_threshold = 75
    obj.needs_improvement_threshold = 60
    obj.save(update_fields=['default_weight', 'productive_threshold', 'needs_improvement_threshold'])


def revert_defaults(apps, schema_editor):
    ProductivitySettings = apps.get_model('tracker_api', 'ProductivitySettings')
    obj, _ = ProductivitySettings.objects.get_or_create(pk=1)
    obj.default_weight = 0.5
    obj.productive_threshold = 70
    obj.needs_improvement_threshold = 50
    obj.save(update_fields=['default_weight', 'productive_threshold', 'needs_improvement_threshold'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker_api', '0013_fix_productivity_settings_default_weight'),
    ]

    operations = [
        migrations.RunPython(update_defaults, revert_defaults),
    ]
