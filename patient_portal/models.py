

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient
from django.utils import timezone

class PatientPortalAccess(models.Model):
    """Patient portal login credentials"""
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
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def reset_login_attempts(self):
        self.login_attempts = 0
        self.locked_until = None
        self.save()
    
    class Meta:
        verbose_name = "Patient Portal Access"
        verbose_name_plural = "Patient Portal Access"


class PatientPortalLog(models.Model):
    """Track patient portal activity"""
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