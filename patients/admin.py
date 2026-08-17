from django.contrib import admin
from .models import Patient, DentalImage

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone', 'email', 'gender', 'registered_at', 'is_active']
    list_filter = ['gender', 'is_active', 'registered_at']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    readonly_fields = ['registered_at']
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'age_years', 'gender')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'address')
        }),
        ('Emergency Contact', {
            'fields': ('next_of_kin', 'next_of_kin_contact')
        }),
        ('Medical History', {
            'fields': ('under_physician', 'physician_details', 'allergies', 'current_medications')
        }),
        ('Dental History', {
            'fields': ('reason_for_visit', 'dental_discomfort', 'discomfort_details', 'last_dental_visit', 'previous_surgery', 'surgery_details')
        }),
        ('System Fields', {
            'fields': ('is_active', 'registered_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(DentalImage)
class DentalImageAdmin(admin.ModelAdmin):
    list_display = ['patient', 'image_type', 'description', 'uploaded_at']
    list_filter = ['image_type', 'uploaded_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'description']
    readonly_fields = ['uploaded_at']
