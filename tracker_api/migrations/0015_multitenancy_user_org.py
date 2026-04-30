from django.db import migrations, models


def backfill_user_organization(apps, schema_editor):
    """Set User.organization from User.department.organization where possible."""
    User = apps.get_model('tracker_api', 'User')
    for user in User.objects.select_related('department').all():
        org_id = None
        if user.department_id and user.department.organization_id:
            org_id = user.department.organization_id
        elif user.managed_organization_id:
            org_id = user.managed_organization_id
        if org_id and user.organization_id != org_id:
            user.organization_id = org_id
            user.save(update_fields=['organization'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tracker_api', '0014_update_productivity_defaults'),
    ]

    operations = [
        # 1. Drop global unique on Department.name and JobPosition.title
        migrations.AlterField(
            model_name='department',
            name='name',
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='jobposition',
            name='title',
            field=models.CharField(db_index=True, max_length=100),
        ),

        # 2. Add organization FK to JobPosition
        migrations.AddField(
            model_name='jobposition',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                help_text='Tenant org this position belongs to. Null = global/default.',
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='positions',
                to='tracker_api.organization',
            ),
        ),

        # 3. Add organization FK to User
        migrations.AddField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                help_text='Tenant organization this user belongs to (denormalized from department)',
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='members',
                to='tracker_api.organization',
            ),
        ),

        # 4. Backfill User.organization from department/managed_organization
        migrations.RunPython(backfill_user_organization, noop_reverse),

        # 5. Add per-org unique constraints
        migrations.AddConstraint(
            model_name='department',
            constraint=models.UniqueConstraint(
                fields=('organization', 'name'),
                name='uniq_dept_name_per_org',
            ),
        ),
        migrations.AddConstraint(
            model_name='jobposition',
            constraint=models.UniqueConstraint(
                fields=('organization', 'title'),
                name='uniq_position_title_per_org',
            ),
        ),
    ]
