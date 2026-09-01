from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
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
        indexes = [
            models.Index(fields=['appointment_date', 'doctor', 'status']),
            models.Index(fields=['patient', '-appointment_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'appointment_time'],
                condition=models.Q(status__in=['scheduled', 'checked_in', 'in_progress']),
                name='unique_active_doctor_slot',
            ),
        ]


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


        # Add to appointments/models.py

class DentalChart(models.Model):
    """Dental chart/odontogram for tracking tooth conditions"""
    
    TOOTH_CONDITION_CHOICES = [
        ('healthy', 'Healthy'),
        ('decay', 'Decay/Cavity'),
        ('filling', 'Filling'),
        ('crown', 'Crown'),
        ('bridge', 'Bridge'),
        ('extraction', 'Extraction'),
        ('implant', 'Implant'),
        ('root_canal', 'Root Canal'),
        ('fracture', 'Fracture'),
        ('missing', 'Missing'),
        ('wear', 'Wear'),
        ('stain', 'Stain'),
        ('other', 'Other'),
    ]
    
    SURFACE_CHOICES = [
        ('occlusal', 'Occlusal'),
        ('mesial', 'Mesial'),
        ('distal', 'Distal'),
        ('buccal', 'Buccal'),
        ('lingual', 'Lingual'),
        ('incisal', 'Incisal'),
        ('labial', 'Labial'),
        ('palatal', 'Palatal'),
    ]
    
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='dental_charts')
    tooth_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(32)], help_text="Universal tooth numbering system (1-32)")
    tooth_name = models.CharField(max_length=50, blank=True, null=True)
    surface = models.CharField(max_length=20, choices=SURFACE_CHOICES, blank=True, null=True)
    condition = models.CharField(max_length=20, choices=TOOTH_CONDITION_CHOICES, default='healthy')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['tooth_number']
        verbose_name = "Dental Chart"
        verbose_name_plural = "Dental Charts"
    
    def __str__(self):
        return f"{self.patient.full_name} - Tooth #{self.tooth_number} - {self.get_condition_display()}"


class ClinicalNote(models.Model):
    """Clinical notes for appointments"""
    
    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE, related_name='clinical_notes')
    note_type = models.CharField(max_length=50, choices=[
        ('history', 'History'),
        ('examination', 'Examination'),
        ('diagnosis', 'Diagnosis'),
        ('treatment', 'Treatment Plan'),
        ('procedure', 'Procedure'),
        ('prescription', 'Prescription'),
        ('referral', 'Referral'),
        ('follow_up', 'Follow Up'),
        ('general', 'General Note'),
    ], default='general')
    content = models.TextField()
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Clinical Note"
        verbose_name_plural = "Clinical Notes"
    
    def __str__(self):
        return f"{self.appointment.patient.full_name} - {self.get_note_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"