from django.db import models
from django.utils import timezone
from patients.models import Patient


class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    @property
    def display_name(self):
        if self.name.startswith('Dr. '):
            return self.name
        return f"Dr. {self.name}"
    
    @property
    def full_name(self):
        return self.display_name
    
    class Meta:
        ordering = ['name']


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - UGX {self.price}"
    
    class Meta:
        ordering = ['name']


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('checked_in', 'Checked In'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    # Patient and Service Info
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    
    # Appointment Details
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.IntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, null=True)
    
    # Treatment Fields
    diagnosis = models.TextField(blank=True, null=True)
    consultation_notes = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    treatment_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    referred_to = models.CharField(max_length=200, blank=True, null=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True, null=True)
    
    # Notification Fields
    notification_email = models.EmailField(blank=True, null=True)
    notification_phone = models.CharField(max_length=20, blank=True, null=True)
    send_reminder = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.patient} - {self.appointment_date} {self.appointment_time}"
    
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']


class Treatment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    treatment_date = models.DateField(auto_now_add=True)
    notes = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.patient} - {self.service} - {self.treatment_date}"


class BookingRequest(models.Model):
    """Public booking request from new patients"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('registered', 'Registered & Booked'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    # Dental Issue
    service_requested = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    dental_issue = models.TextField(help_text="Describe your dental problem/concern")
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True, help_text="Admin notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # When registered as patient
    registered_patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.status}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Booking Request"
        verbose_name_plural = "Booking Requests"