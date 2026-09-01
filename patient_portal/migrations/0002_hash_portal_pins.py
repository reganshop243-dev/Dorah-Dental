import hashlib
from django.db import migrations, models


def hash_existing_pins(apps, schema_editor):
    Access = apps.get_model('patient_portal', 'PatientPortalAccess')
    for access in Access.objects.all().only('id', 'portal_pin'):
        pin = access.portal_pin or ''
        # Existing installs stored raw numeric PINs; new installs store SHA-256.
        if len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin.lower()):
            access.portal_pin = hashlib.sha256(pin.encode()).hexdigest()
            access.save(update_fields=['portal_pin'])


class Migration(migrations.Migration):
    dependencies = [('patient_portal', '0001_initial')]
    operations = [
        migrations.AlterField(
            model_name='patientportalaccess',
            name='portal_pin',
            field=models.CharField(max_length=128, help_text='Hashed portal PIN'),
        ),
        migrations.RunPython(hash_existing_pins, migrations.RunPython.noop),
    ]
