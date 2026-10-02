from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient
from appointments.models import Appointment, Doctor
from django.utils import timezone


class PatientPortalAccess(models.Model):
    """Patient portal login credentials."""
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='portal_access')
    portal_pin = models.CharField(max_length=128, help_text="Hashed portal PIN")
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.full_name} - Portal Access"

    def is_locked(self):
        return bool(self.locked_until and timezone.now() < self.locked_until)

    def reset_login_attempts(self):
        self.login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['login_attempts', 'locked_until', 'updated_at'])

    class Meta:
        verbose_name = "Patient Portal Access"
        verbose_name_plural = "Patient Portal Access"


class PatientPortalLog(models.Model):
    """Track patient portal activity."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='portal_logs')
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.full_name} - {self.action} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Patient Portal Log"
        verbose_name_plural = "Patient Portal Logs"


class PortalOffer(models.Model):
    """Clinic promotion visible to patients when published and within its validity dates."""
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='portal/offers/', blank=True, null=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_published', 'valid_from', 'valid_until']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_current(self):
        today = timezone.localdate()
        return (
            self.is_published
            and (not self.valid_from or self.valid_from <= today)
            and (not self.valid_until or self.valid_until >= today)
        )


class PatientConversation(models.Model):
    """Secure patient-to-clinic/doctor conversation."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='portal_conversations')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True, related_name='portal_conversations')
    subject = models.CharField(max_length=200, default='General enquiry')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['patient', 'status', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.patient.full_name} — {self.subject}"


class PatientMessage(models.Model):
    """Message belonging to a patient portal conversation."""
    SENDER_CHOICES = [
        ('patient', 'Patient'),
        ('staff', 'Clinic/Doctor'),
    ]

    conversation = models.ForeignKey(PatientConversation, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES, default='patient')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_portal_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender_type', 'read_at']),
        ]

    def __str__(self):
        return f"{self.conversation.subject} — {self.get_sender_type_display()}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.sender_type == 'staff':
            from .services import create_portal_notification
            create_portal_notification(
                self.conversation.patient,
                'New message from the clinic',
                f'You have a new reply regarding “{self.conversation.subject}”.',
                'message',
                conversation=self.conversation,
                url=f'/portal/messages/{self.conversation_id}/',
            )


class PortalNotification(models.Model):
    """Private notification visible only to the linked patient."""
    TYPE_CHOICES = [
        ('appointment', 'Appointment'),
        ('payment', 'Payment'),
        ('message', 'Message'),
        ('offer', 'Offer'),
        ('clinic', 'Clinic Announcement'),
        ('system', 'System'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='portal_notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField()
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='portal_notifications')
    conversation = models.ForeignKey(PatientConversation, on_delete=models.CASCADE, null=True, blank=True, related_name='portal_notifications')
    url = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'is_read', '-created_at']),
            models.Index(fields=['appointment', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.patient.full_name} — {self.title}"
