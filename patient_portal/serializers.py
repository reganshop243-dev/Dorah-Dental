from rest_framework import serializers
from .models import PatientPortalAccess, PatientPortalLog
from patients.models import Patient

class PatientPortalAccessSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    is_locked = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PatientPortalAccess
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'login_attempts', 'locked_until']

class PatientPortalLogSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = PatientPortalLog
        fields = '__all__'
        read_only_fields = ['timestamp']
