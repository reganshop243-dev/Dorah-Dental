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


class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - UGX {self.price}"


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
    notes = models.TextField(blank=True)
    
    # Treatment Fields
    consultation_notes = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    diagnosis = models.CharField(max_length=500, blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    follow_up_notes = models.TextField(blank=True, null=True)
    treatment_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    referred_to = models.CharField(max_length=200, blank=True, null=True)
    
    # Notification Fields
    notification_email = models.EmailField(blank=True, null=True, help_text="Email for appointment reminders")
    notification_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone for SMS reminders")
    send_reminder = models.BooleanField(default=True, help_text="Send reminder for this appointment")
    reminder_sent = models.BooleanField(default=False, help_text="Has reminder been sent")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.patient} - {self.appointment_date} {self.appointment_time}"


class Treatment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    treatment_date = models.DateField(auto_now_add=True)
    notes = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    next_appointment = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.patient} - {self.service} - {self.treatment_date}"