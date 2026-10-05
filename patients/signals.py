"""
Signal handlers for the patients app.

Keeps denormalized copies of patient data on related models (e.g. Invoice)
in sync whenever a Patient is saved.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Patient


@receiver(post_save, sender=Patient, dispatch_uid='patients.sync_patient_to_invoices')
def sync_patient_to_invoices(sender, instance, **kwargs):
    """
    When a Patient is saved, update the cached patient_name and
    patient_phone on every Invoice that references them.
    """
    from billing.models import Invoice  # local import avoids circular import

    full_name = f"{instance.first_name or ''} {instance.last_name or ''}".strip()
    phone = instance.phone or ''

    # .update() is a single SQL UPDATE — fast even for many invoices
    Invoice.objects.filter(patient=instance).update(
        patient_name=full_name,
        patient_phone=phone,
    )