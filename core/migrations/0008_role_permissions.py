from django.db import migrations, models


def seed_role_permissions(apps, schema_editor):
    RolePermission = apps.get_model('core', 'RolePermission')
    from core.permissions import PERMISSION_CATALOG, BASELINE
    for role_code in BASELINE:
        for permission_code, _, _ in PERMISSION_CATALOG:
            RolePermission.objects.create(
                role_code=role_code,
                permission_code=permission_code,
                enabled=permission_code in BASELINE.get(role_code, set()),
                is_primary=permission_code in BASELINE.get(role_code, set()),
            )


class Migration(migrations.Migration):
    dependencies = [('core', '0007_userprofile_additional_roles')]
    operations = [
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_code', models.CharField(max_length=20)),
                ('permission_code', models.CharField(max_length=100)),
                ('enabled', models.BooleanField(default=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['role_code', 'permission_code']},
        ),
        migrations.AddConstraint(
            model_name='rolepermission',
            constraint=models.UniqueConstraint(fields=('role_code','permission_code'), name='core_role_permission_unique'),
        ),
        migrations.RunPython(seed_role_permissions, migrations.RunPython.noop),
    ]
