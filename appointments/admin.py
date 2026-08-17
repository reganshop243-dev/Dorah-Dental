from django.contrib import admin
from .models import Appointment, Doctor, Service, Treatment, BookingRequest, DentalChart, ClinicalNote

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialization', 'phone', 'email', 'is_active']
    list_filter = ['specialization', 'is_active']
    search_fields = ['name', 'specialization', 'phone', 'email']
    ordering = ['name']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_minutes', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['name']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'service', 'appointment_date', 'appointment_time', 'status']
    list_filter = ['status', 'appointment_date', 'doctor']
    search_fields = ['patient__first_name', 'patient__last_name', 'doctor__name']
    date_hierarchy = 'appointment_date'
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'doctor', 'service')
        }),
        ('Appointment Details', {
            'fields': ('appointment_date', 'appointment_time', 'duration_minutes', 'status', 'notes')
        }),
        ('Treatment Fields', {
            'fields': ('diagnosis', 'consultation_notes', 'treatment_plan', 'prescription', 'treatment_cost', 'referred_to', 'follow_up_date', 'follow_up_notes')
        }),
        ('Notification Fields', {
            'fields': ('notification_email', 'notification_phone', 'send_reminder', 'reminder_sent')
        }),
        ('System Fields', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'service', 'treatment_date', 'amount']
    search_fields = ['patient__first_name', 'patient__last_name', 'doctor__name']
    list_filter = ['treatment_date']
    date_hierarchy = 'treatment_date'

@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'service_requested', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(DentalChart)
class DentalChartAdmin(admin.ModelAdmin):
    list_display = ['patient', 'tooth_number', 'condition', 'surface', 'created_at']
    list_filter = ['condition', 'surface']
    search_fields = ['patient__first_name', 'patient__last_name', 'tooth_number']

@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'note_type', 'created_by', 'created_at']
    list_filter = ['note_type', 'created_at']
    search_fields = ['appointment__patient__first_name', 'appointment__patient__last_name', 'content']
    date_hierarchy = 'created_at'
