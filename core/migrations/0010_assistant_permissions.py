from django.db import migrations


ASSISTANT_PERMISSIONS = {
    'patients.view',
    'patients.images',
    'patients.contacts.request',
    'appointments.view',
    'appointments.create',
    'appointments.edit',
    'appointments.status',
    'dental.view',
    'dental.create',
    'dental.edit',
    'clinical.notes.view',
    'clinical.notes.create',
}


def update_assistant_permissions(apps, schema_editor):
    RolePermission = apps.get_model('core', 'RolePermission')
    for permission_code in ASSISTANT_PERMISSIONS:
        RolePermission.objects.update_or_create(
            role_code='assistant',
            permission_code=permission_code,
            defaults={'enabled': True, 'is_primary': True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0009_new_permissions'),
    ]

    operations = [
        migrations.RunPython(
            update_assistant_permissions,
            migrations.RunPython.noop,
        ),
    ]
