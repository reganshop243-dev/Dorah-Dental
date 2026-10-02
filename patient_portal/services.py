from datetime import datetime, timedelta
from django.urls import reverse
from django.utils import timezone

from .models import PortalNotification


def create_portal_notification(patient, title, message, notification_type='system', appointment=None,
                                conversation=None, url=''):
    """Create one private patient notification, suppressing exact duplicates."""
    qs = PortalNotification.objects.filter(
        patient=patient,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    if appointment is not None:
        qs = qs.filter(appointment=appointment)
    else:
        qs = qs.filter(appointment__isnull=True)
    if conversation is not None:
        qs = qs.filter(conversation=conversation)
    else:
        qs = qs.filter(conversation__isnull=True)
    if qs.exists():
        return qs.first()
    return PortalNotification.objects.create(
        patient=patient,
        notification_type=notification_type,
        title=title,
        message=message,
        appointment=appointment,
        conversation=conversation,
        url=url,
    )


def notify_appointment_event(appointment, event='created'):
    """Create a patient-portal notification for a meaningful appointment event."""
    patient = appointment.patient
    doctor = appointment.doctor.display_name if appointment.doctor_id else 'your dentist'
    service = appointment.service.name if appointment.service_id else 'your dental appointment'
    date_text = appointment.appointment_date.strftime('%A, %d %B %Y')
    time_text = appointment.appointment_time.strftime('%I:%M %p')

    if event == 'created':
        title = 'Appointment confirmed'
        message = f'Your {service} appointment is scheduled for {date_text} at {time_text} with {doctor}.'
    elif event == 'updated':
        title = 'Appointment updated'
        message = f'Your {service} appointment has been updated. It is now scheduled for {date_text} at {time_text} with {doctor}.'
    elif event == 'cancelled':
        title = 'Appointment cancelled'
        message = f'Your appointment for {date_text} at {time_text} has been cancelled. Please contact the clinic if you need a new appointment.'
    else:
        status = appointment.get_status_display()
        title = f'Appointment {status.lower()}'
        message = f'Your appointment on {date_text} at {time_text} is now marked as {status}.'

    return create_portal_notification(
        patient, title, message, 'appointment', appointment=appointment,
        url=reverse('patient_portal:appointments'),
    )


def sync_upcoming_appointment_reminders(patient):
    """Ensure portal reminders exist for the patient's next appointments."""
    now = timezone.localtime()
    today = now.date()
    upcoming = patient.appointment_set.filter(
        appointment_date__gte=today,
        status__in=['scheduled', 'checked_in'],
    ).select_related('doctor', 'service').order_by('appointment_date', 'appointment_time')[:10]

    for appointment in upcoming:
        appointment_dt = timezone.make_aware(datetime.combine(appointment.appointment_date, appointment.appointment_time))
        if appointment_dt <= now:
            continue
        hours = (appointment_dt - now).total_seconds() / 3600
        if hours <= 26:
            title = 'Appointment reminder'
            message = (
                f'Reminder: your appointment is on {appointment.appointment_date.strftime("%A, %d %B %Y")} '
                f'at {appointment.appointment_time.strftime("%I:%M %p")} with {appointment.doctor.display_name}.'
            )
            create_portal_notification(
                patient, title, message, 'appointment', appointment=appointment,
                url=reverse('patient_portal:appointments'),
            )
