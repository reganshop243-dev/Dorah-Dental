from rest_framework import serializers
from .models import Appointment, Doctor, Service, Treatment, BookingRequest, DentalChart, ClinicalNote

class DoctorSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'display_name', 'specialization', 'phone', 'email', 'is_active']
    
    def get_display_name(self, obj):
        return obj.display_name

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration_minutes', 'is_active']

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.display_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status_display(self, obj):
        return dict(Appointment.STATUS_CHOICES).get(obj.status, obj.status)

class TreatmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.display_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = Treatment
        fields = '__all__'

class BookingRequestSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service_requested.name', read_only=True)
    full_name = serializers.CharField(source='full_name', read_only=True)
    
    class Meta:
        model = BookingRequest
        fields = '__all__'

class DentalChartSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    condition_display = serializers.SerializerMethodField()
    surface_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DentalChart
        fields = '__all__'
    
    def get_condition_display(self, obj):
        return dict(DentalChart.TOOTH_CONDITION_CHOICES).get(obj.condition, obj.condition)
    
    def get_surface_display(self, obj):
        return dict(DentalChart.SURFACE_CHOICES).get(obj.surface, obj.surface)

class ClinicalNoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    note_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalNote
        fields = '__all__'
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_note_type_display(self, obj):
        return dict(ClinicalNote.NOTE_TYPE_CHOICES).get(obj.note_type, obj.note_type)
