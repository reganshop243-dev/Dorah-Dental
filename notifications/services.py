"""
Notification Service - Send SMS and Email reminders
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from appointments.models import Appointment
from core.models import CompanySettings
from .models import NotificationSetting, NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles sending SMS and Email notifications"""
    
    def __init__(self):
        self.settings = self.get_settings()
    
    def get_settings(self):
        """Get notification settings"""
        try:
            return NotificationSetting.objects.first()
        except:
            # Create default settings if none exist
            return NotificationSetting.objects.create()
    
    def _clean_phone_number(self, phone_number):
        """Clean phone number for SMS sending"""
        if not phone_number:
            return None
        
        # Remove spaces, dashes, brackets
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # If number starts with 0 (Ugandan format), replace with 256
        if phone.startswith('0') and len(phone) == 10:
            phone = '256' + phone[1:]
        
        # If number starts with +, remove it
        if phone_number.startswith('+'):
            phone = phone_number[1:].strip()
            phone = ''.join(filter(str.isdigit, phone))
        
        # Ensure it's a valid Ugandan number (starts with 256)
        if not phone.startswith('256'):
            if len(phone) == 9 and phone.startswith('7'):
                phone = '256' + phone
            else:
                phone = '256' + phone
        
        return phone
    
    def _clinic_info(self):
        """Use the editable Company Settings values for all patient messages."""
        try:
            company = CompanySettings.get_settings()
            return {
                'clinic_name': company.business_short_name or company.business_name,
                'clinic_phone': company.phone or company.notification_phone or '',
                'clinic_email': company.email or company.notification_email or '',
                'clinic_address': company.address or '',
            }
        except Exception:
            return {
                'clinic_name': getattr(settings, 'BUSINESS_SHORT_NAME', "Dora's Dental Gem"),
                'clinic_phone': getattr(settings, 'BUSINESS_PHONE', ''),
                'clinic_email': getattr(settings, 'BUSINESS_EMAIL', ''),
                'clinic_address': getattr(settings, 'BUSINESS_ADDRESS', ''),
            }

    def send_appointment_reminder(self, appointment, force=False):
        """Send configured reminder channels once the configured lead time is reached."""
        try:
            settings_obj = self.settings
            if not settings_obj.enable_reminders or not appointment.send_reminder:
                return False

            if not force and not self.should_send_reminder(appointment):
                return False

            data = self.prepare_data(appointment)
            requested_channels = []
            if settings_obj.channel in ['email', 'both'] and appointment.patient.email:
                requested_channels.append('email')
            if settings_obj.channel in ['sms', 'both'] and appointment.patient.phone:
                requested_channels.append('sms')

            success = False
            for channel in requested_channels:
                if NotificationLog.objects.filter(appointment=appointment, channel=channel, status='sent').exists():
                    continue
                if channel == 'email':
                    success = self.send_email_reminder(appointment, data) or success
                elif channel == 'sms':
                    success = self.send_sms_reminder(appointment, data) or success

            sent_channels = set(NotificationLog.objects.filter(
                appointment=appointment, status='sent'
            ).values_list('channel', flat=True))
            all_requested_sent = bool(requested_channels) and all(channel in sent_channels for channel in requested_channels)
            if all_requested_sent and not appointment.reminder_sent:
                appointment.reminder_sent = True
                appointment.save(update_fields=['reminder_sent', 'updated_at'])

            return success
        except Exception as e:
            logger.exception("Error sending reminder for appointment %s: %s", appointment.pk, e)
            return False

    def should_send_reminder(self, appointment):
        """Return true when the appointment has reached the configured reminder time."""
        if appointment.reminder_sent:
            return False

        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )
        appointment_datetime = timezone.make_aware(
            appointment_datetime,
            timezone.get_current_timezone()
        )
        reminder_time = appointment_datetime - timedelta(hours=self.settings.reminder_hours_before)
        return timezone.now() >= reminder_time

    def prepare_data(self, appointment):
        """Prepare template data using current Company Settings."""
        clinic = self._clinic_info()
        public_base = getattr(
            settings, 'PUBLIC_BASE_URL', 'https://dorahdental.world'
        ).rstrip('/')
        portal_url = public_base + '/'
        return {
            'patient_name': appointment.patient.full_name,
            'appointment_date': appointment.appointment_date.strftime('%A, %B %d, %Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'doctor_name': appointment.doctor.name,
            'service_name': appointment.service.name,
            'portal_url': portal_url,
            'clinic_url': public_base,
            **clinic,
        }

    def send_email_reminder(self, appointment, data):
        """Send email reminder"""
        try:
            settings_obj = self.settings
            template = Template(settings_obj.email_template)
            context = Context(data)
            message = template.render(context)
            
            send_mail(
                subject=settings_obj.email_subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@dorasdentalgem.com',
                recipient_list=[appointment.patient.email],
                fail_silently=False,
            )
            
            NotificationLog.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                channel='email',
                sent_to=appointment.patient.email,
                subject=settings_obj.email_subject,
                message=message,
                status='sent',
                sent_at=timezone.now()
            )
            
            logger.info(f"Email reminder sent to {appointment.patient.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email reminder: {e}")
            NotificationLog.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                channel='email',
                sent_to=appointment.patient.email,
                message=str(e),
                status='failed',
                error_message=str(e)
            )
    
    def send_sms_reminder(self, appointment, data):
        """Send SMS reminder using Yoola SMS"""
        try:
            from .yoola_sms import YoolaSMS
            
            settings_obj = self.settings
            
            phone_number = appointment.notification_phone or appointment.patient.phone
            
            if not phone_number:
                logger.warning(f"Patient {appointment.patient.full_name} has no phone number.")
                return False
            
            phone_number = self._clean_phone_number(phone_number)
            
            if not phone_number:
                logger.warning(f"Invalid phone number for {appointment.patient.full_name}")
                return False
            
            template = Template(settings_obj.sms_template)
            context = Context(data)
            message = template.render(context).strip()

            # Always include a clickable patient portal link in appointment SMS.
            # Keep the URL intact even when the SMS is longer than the provider limit.
            portal_url = data.get('portal_url') or 'https://dorahdental.world/'
            if portal_url not in message:
                link_text = f" Portal: {portal_url}"
                available = 300 - len(link_text)
                message = message[:max(0, available)].rstrip() + link_text
            elif len(message) > 300:
                message = message[:300]
            
            yoola = YoolaSMS()
            result = yoola.send_sms(phone_number, message)
            
            if result.get('success'):
                NotificationLog.objects.create(
                    appointment=appointment,
                    patient=appointment.patient,
                    channel='sms',
                    sent_to=phone_number,
                    message=message,
                    status='sent',
                    sent_at=timezone.now()
                )
                logger.info(f"SMS reminder sent to {phone_number}")
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"SMS failed for {phone_number}: {error_msg}")
                NotificationLog.objects.create(
                    appointment=appointment,
                    patient=appointment.patient,
                    channel='sms',
                    sent_to=phone_number,
                    message=message,
                    status='failed',
                    error_message=error_msg
                )
                return False
            
        except Exception as e:
            logger.error(f"Error sending SMS reminder: {e}")
            NotificationLog.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                channel='sms',
                sent_to=appointment.patient.phone or 'unknown',
                message=str(e),
                status='failed',
                error_message=str(e)
            )
            return False


def send_appointment_reminders():
    """Send reminders for all upcoming appointments"""
    service = NotificationService()
    
    now = timezone.now()
    next_week = now + timedelta(days=7)
    
    appointments = Appointment.objects.filter(
        appointment_date__gte=now.date(),
        appointment_date__lte=next_week.date(),
        status__in=['scheduled', 'checked_in']
    )
    
    count = 0
    for appointment in appointments:
        service.send_appointment_reminder(appointment)
        count += 1
    
    return count

# ---------------------------------------------------------------------------
# In-app + Web Push notifications
# ---------------------------------------------------------------------------
def create_user_notification(*, recipient, notification_type, title, message, url='', appointment=None, patient=None, send_push=True):
    from .models import UserNotification
    notification = UserNotification.objects.create(
        recipient=recipient, notification_type=notification_type, title=title,
        message=message, url=url or '', appointment=appointment, patient=patient,
    )
    if send_push:
        send_web_push(notification)
    return notification


def send_web_push(notification):
    """Send a Web Push notification to all subscriptions for a user."""
    from .models import PushSubscription
    public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
    private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    subject = getattr(settings, 'VAPID_SUBJECT', '')
    if not public_key or not private_key or not subject:
        logger.warning('Web Push skipped: VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY/VAPID_SUBJECT are not configured.')
        return False
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.error('Web Push unavailable: pywebpush is not installed.')
        return False

    payload = {
        'title': notification.title,
        'body': notification.message,
        'url': notification.url or '/',
        'notification_id': notification.pk,
    }
    import json
    delivered = False
    for subscription in PushSubscription.objects.filter(user=notification.recipient):
        try:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
                },
                data=json.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={'sub': subject},
            )
            delivered = True
        except WebPushException as exc:
            logger.warning('Web Push failed for subscription %s: %s', subscription.pk, exc)
            if getattr(exc, 'response', None) is not None and getattr(exc.response, 'status_code', None) in (404, 410):
                subscription.delete()
        except Exception as exc:
            logger.exception('Unexpected Web Push error: %s', exc)
    return delivered


def notify_appointment_assigned(appointment):
    from django.contrib.auth.models import User
    users = User.objects.filter(profile__doctor=appointment.doctor, is_active=True).distinct()
    for user in users:
        create_user_notification(
            recipient=user,
            notification_type='appointment_assigned',
            title='New appointment assigned',
            message=f'{appointment.patient.full_name} — {appointment.appointment_date:%d %b %Y} at {appointment.appointment_time:%H:%M}.',
            url=f'/appointments/appointments/{appointment.pk}/',
            appointment=appointment, patient=appointment.patient,
        )


def notify_appointment_completed(appointment):
    from django.contrib.auth.models import User
    users = User.objects.filter(profile__role='admin', is_active=True).distinct()
    for user in users:
        create_user_notification(
            recipient=user,
            notification_type='appointment_completed',
            title='Appointment completed',
            message=f"Dr. {appointment.doctor.name} completed {appointment.patient.full_name}'s appointment.",
            url=f'/appointments/appointments/{appointment.pk}/',
            appointment=appointment, patient=appointment.patient,
        )
