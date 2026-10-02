from .models import Patient, PatientMessage


def portal_context(request):
    if not request.session.get('patient_portal_logged_in'):
        return {}
    patient_id = request.session.get('patient_portal_patient_id')
    try:
        patient = Patient.objects.get(pk=patient_id, is_active=True)
    except (Patient.DoesNotExist, TypeError, ValueError):
        return {}
    return {
        'portal_patient': patient,
        'portal_unread_notifications': patient.portal_notifications.filter(is_read=False).count(),
        'portal_unread_messages': PatientMessage.objects.filter(
            conversation__patient=patient, sender_type='staff', read_at__isnull=True
        ).count(),
    }
