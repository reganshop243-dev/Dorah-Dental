"""
Notification Service - Send SMS and Email reminders
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from appointments.models import Appointment
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
    
    def send_appointment_reminder(self, appointment):
        """Send appointment reminder via SMS and/or Email"""
        try:
            settings_obj = self.settings
            if not settings_obj.enable_reminders:
                return
            
            if not self.should_send_reminder(appointment):
                return
            
            data = self.prepare_data(appointment)
            
            if settings_obj.channel in ['email', 'both']:
                self.send_email_reminder(appointment, data)
            
            if settings_obj.channel in ['sms', 'both']:
                self.send_sms_reminder(appointment, data)
            
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
    
    def should_send_reminder(self, appointment):
        """Check if reminder should be sent"""
        if NotificationLog.objects.filter(
            appointment=appointment,
            status='sent'
        ).exists():
            return False
        
        appointment_datetime = datetime.combine(
            appointment.appointment_date,
            appointment.appointment_time
        )
        now = timezone.now()
        hours_before = self.settings.reminder_hours_before
        reminder_time = appointment_datetime - timedelta(hours=hours_before)
        
        return now >= reminder_time
    
    def prepare_data(self, appointment):
        """Prepare data for templates"""
        return {
            'patient_name': appointment.patient.full_name,
            'appointment_date': appointment.appointment_date.strftime('%A, %B %d, %Y'),
            'appointment_time': appointment.appointment_time.strftime('%I:%M %p'),
            'doctor_name': appointment.doctor.name,
            'service_name': appointment.service.name,
            'clinic_name': getattr(settings, 'BUSINESS_SHORT_NAME', "Dora's Dental Gem"),
            'clinic_phone': getattr(settings, 'BUSINESS_PHONE', '+256 700 000 000'),
            'clinic_email': getattr(settings, 'BUSINESS_EMAIL', 'info@dorasdentalgem.com'),
            'clinic_address': getattr(settings, 'BUSINESS_ADDRESS', 'Kampala, Uganda'),
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
            message = template.render(context)
            
            if len(message) > 300:
                message = message[:297] + "..."
            
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