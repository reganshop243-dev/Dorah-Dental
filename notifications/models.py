from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from appointments.models import Appointment, Patient


class NotificationSetting(models.Model):
    """Settings for notifications"""
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Both'),
    ]
    
    # Enable/disable notifications
    enable_reminders = models.BooleanField(default=True)
    reminder_hours_before = models.PositiveIntegerField(default=24, help_text="Hours before appointment to send reminder")
    reminder_days_before = models.PositiveIntegerField(default=1, help_text="Days before appointment to send reminder")
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='both')
    
    # Email settings
    email_subject = models.CharField(max_length=200, default="Appointment Reminder - Dora's Dental Gem")
    email_template = models.TextField(default="""
Dear {{ patient_name }},

This is a reminder of your upcoming appointment at Dora's Dental Gem.

Appointment Details:
- Date: {{ appointment_date }}
- Time: {{ appointment_time }}
- Doctor: {{ doctor_name }}
- Service: {{ service_name }}

Please arrive 15 minutes before your appointment.

If you need to reschedule, please call us at {{ clinic_phone }}.

Thank you,
Dora's Dental Gem Team
""")
    
    # SMS settings
    sms_template = models.TextField(default="Dora's Dental Gem Reminder: {{ patient_name }}, your appointment is on {{ appointment_date }} at {{ appointment_time }} with Dr. {{ doctor_name }}. Call {{ clinic_phone }} to reschedule.")
    
    # Twilio settings
    twilio_account_sid = models.CharField(max_length=200, blank=True, null=True)
    twilio_auth_token = models.CharField(max_length=200, blank=True, null=True)
    twilio_phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Notification Settings"
    
    def __str__(self):
        return "Notification Settings"


class NotificationLog(models.Model):
    """Log of all notifications sent"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notifications')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=10, choices=[('email', 'Email'), ('sms', 'SMS')])
    sent_to = models.CharField(max_length=200)  # Email address or phone number
    subject = models.CharField(max_length=500, blank=True, null=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Notification Logs"
    
    def __str__(self):
        return f"{self.get_channel_display()} to {self.sent_to} - {self.status}"