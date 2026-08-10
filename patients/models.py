from django.db import models
from datetime import date


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(blank=True, null=True)
    age_years = models.IntegerField(blank=True, null=True, help_text="If date of birth is unknown, enter age in years")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Profile Picture
    profile_picture = models.ImageField(upload_to='patient_photos/', blank=True, null=True)
    
    # Contact Information
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Emergency Contact / Next of Kin
    next_of_kin = models.CharField(max_length=200, blank=True, null=True)
    next_of_kin_contact = models.CharField(max_length=20, blank=True, null=True)
    
    # Medical History
    under_physician = models.CharField(max_length=3, blank=True, null=True, choices=[('yes', 'Yes'), ('no', 'No')])
    physician_details = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True)
    current_medications = models.TextField(blank=True, null=True)
    
    # Dental History
    reason_for_visit = models.TextField(blank=True, null=True)
    dental_discomfort = models.CharField(max_length=3, blank=True, null=True, choices=[('yes', 'Yes'), ('no', 'No')])
    discomfort_details = models.TextField(blank=True, null=True)
    last_dental_visit = models.DateField(blank=True, null=True)
    previous_surgery = models.CharField(max_length=3, blank=True, null=True, choices=[('yes', 'Yes'), ('no', 'No')])
    surgery_details = models.TextField(blank=True, null=True)
    # System fields - allow backdating
    registered_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate age from date of birth or use age_years"""
        if self.date_of_birth:
            today = date.today()
            age = today.year - self.date_of_birth.year
            if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
                age -= 1
            return age
        return self.age_years
    
    @property
    def age_display(self):
        """Get age with years label"""
        age = self.age
        if age is None:
            return "N/A"
        if age == 0:
            return "< 1 year"
        return f"{age} years"
    
    @property
    def profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return '/static/images/default-avatar.png'
    
    def __str__(self):
        return self.full_name
    
    class Meta:
        ordering = ['first_name', 'last_name']
        verbose_name = "Patient"
        verbose_name_plural = "Patients"


class DentalImage(models.Model):
    IMAGE_TYPES = [
        ('clinical', 'Clinical Photo'),
        ('xray', 'X-Ray'),
        ('treatment', 'Treatment Photo'),
        ('before', 'Before Treatment'),
        ('after', 'After Treatment'),
        ('surgery', 'Surgery Photo'),
        ('other', 'Other'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dental_images')
    image = models.ImageField(upload_to='dental_images/')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='clinical')
    description = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.get_image_type_display()} - {self.uploaded_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Dental Image"
        verbose_name_plural = "Dental Images"