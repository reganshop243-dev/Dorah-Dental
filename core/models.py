from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
        ('accountant', 'Accountant'),
        ('nurse', 'Nurse'),
        ('assistant', 'Assistant'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='receptionist')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Doctor linking
    doctor = models.OneToOneField('appointments.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profile')
    
    # OTP fields
    phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    otp_attempts = models.IntegerField(default=0)  # Fixed: added default=0
    last_otp_sent = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
    
    @property
    def role_display(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def can_request_otp(self):
        """Check if user can request a new OTP (once per day)"""
        if not self.last_otp_sent:
            return True
        # Allow OTP request once per day
        time_diff = timezone.now() - self.last_otp_sent
        return time_diff.total_seconds() >= 86400  # 24 hours
    
    def is_otp_valid(self, code):
        """Check if OTP code is valid and not expired (5 minutes expiry)"""
        if not self.otp_code or not self.otp_created_at:
            return False
        if self.otp_code != code:
            return False
        # OTP expires after 5 minutes
        time_diff = timezone.now() - self.otp_created_at
        return time_diff.total_seconds() <= 300  # 5 minutes
    
    class Meta:
        ordering = ['user__username']


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class CompanySettings(models.Model):
    """Company/Business settings"""
    # Business Info
    business_name = models.CharField(max_length=200, default="Dora's Dental Gem")
    business_short_name = models.CharField(max_length=100, default="Dora's Dental")
    tagline = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Contact Info
    phone = models.CharField(max_length=20, default="+256 700 000 000")
    email = models.EmailField(default="info@dorasdentalgem.com")
    website = models.URLField(blank=True, null=True)
    address = models.TextField(default="Kampala, Uganda")
    
    # Social Media
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    youtube = models.URLField(blank=True, null=True)
    
    # Business Hours
    monday_hours = models.CharField(max_length=100, blank=True, null=True)
    tuesday_hours = models.CharField(max_length=100, blank=True, null=True)
    wednesday_hours = models.CharField(max_length=100, blank=True, null=True)
    thursday_hours = models.CharField(max_length=100, blank=True, null=True)
    friday_hours = models.CharField(max_length=100, blank=True, null=True)
    saturday_hours = models.CharField(max_length=100, blank=True, null=True)
    sunday_hours = models.CharField(max_length=100, blank=True, null=True)
    
    # Logo and Branding
    logo = models.ImageField(upload_to='company/', blank=True, null=True)
    favicon = models.ImageField(upload_to='company/', blank=True, null=True)
    
    # Currency and Region
    currency = models.CharField(max_length=10, default="UGX")
    currency_symbol = models.CharField(max_length=5, default="UGX")
    timezone = models.CharField(max_length=50, default="Africa/Nairobi")
    country = models.CharField(max_length=100, default="Uganda")
    
    # Tax Settings
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Invoice Settings
    invoice_prefix = models.CharField(max_length=10, default="INV-")
    invoice_footer = models.TextField(blank=True, null=True)
    
    # Notification Settings
    notification_email = models.EmailField(blank=True, null=True)
    notification_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # System
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Company Settings"
        verbose_name_plural = "Company Settings"
    
    def __str__(self):
        return self.business_name
    
    @classmethod
    def get_settings(cls):
        """Get or create company settings"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings





