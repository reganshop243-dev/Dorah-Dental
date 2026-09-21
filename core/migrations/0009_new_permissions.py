from django.db import migrations

NEW_PERMISSIONS = [
    ('patients.contacts.view', False),
    ('patients.contacts.request', False),
    ('patients.contacts.approve', False),
    ('notifications.view', False),
    ('notifications.push', False),
]

def seed(apps, schema_editor):
    RolePermission = apps.get_model('core', 'RolePermission')
    baselines = {
        'admin': {code for code, _ in NEW_PERMISSIONS},
        'doctor': {'patients.contacts.request', 'notifications.view', 'notifications.push'},
        'nurse': {'notifications.view', 'notifications.push'},
        'receptionist': {'notifications.view'},
        'accountant': {'notifications.view', 'notifications.push'},
        'assistant': {'notifications.view', 'notifications.push'},
    }
    for role, _ in baselines.items():
        for code, _ in NEW_PERMISSIONS:
            enabled = code in baselines.get(role, set())
            RolePermission.objects.update_or_create(
                role_code=role, permission_code=code,
                defaults={'enabled': enabled, 'is_primary': enabled},
            )

class Migration(migrations.Migration):
    dependencies = [('core', '0008_role_permissions')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
