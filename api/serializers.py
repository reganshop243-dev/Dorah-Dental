from rest_framework import serializers
from patients.models import Patient, DentalImage
from appointments.models import Appointment, Service, Doctor
from billing.models import Invoice
from core.models import UserProfile


# ==================== PATIENT SERIALIZERS ====================

class PatientSerializer(serializers.ModelSerializer):
    """Patient information for mobile apps"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'full_name', 'phone', 'email', 
                  'date_of_birth', 'age', 'gender', 'address', 'registered_at']
    
    def get_full_name(self, obj):
        return obj.full_name
    
    def get_age(self, obj):
        return obj.age


class PatientDetailSerializer(PatientSerializer):
    """Detailed patient info with images"""
    dental_images = serializers.SerializerMethodField()
    
    class Meta(PatientSerializer.Meta):
        fields = PatientSerializer.Meta.fields + ['dental_images', 'medical_history', 'allergies']
    
    def get_dental_images(self, obj):
        images = obj.dental_images.filter(is_active=True)
        return [{'id': img.id, 'image': img.image.url, 'description': img.description} 
                for img in images]


# ==================== SERVICE SERIALIZERS ====================

class ServiceSerializer(serializers.ModelSerializer):
    """Service information for mobile apps"""
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'duration_minutes', 'is_active']


# ==================== DOCTOR SERIALIZERS ====================

class DoctorSerializer(serializers.ModelSerializer):
    """Doctor information"""
    display_name = serializers.CharField(source='display_name')
    
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'display_name', 'specialization', 'phone', 'email', 'is_active']


# ==================== APPOINTMENT SERIALIZERS ====================

class AppointmentSerializer(serializers.ModelSerializer):
    """Appointment information for mobile apps"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone', read_only=True)
    doctor_name = serializers.CharField(source='doctor.display_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_price = serializers.DecimalField(source='service.price', read_only=True, max_digits=10, decimal_places=2)
    
    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_name', 'patient_phone', 'doctor', 'doctor_name',
                  'service', 'service_name', 'service_price', 'appointment_date', 'appointment_time',
                  'status', 'notes', 'diagnosis', 'created_at']
        read_only_fields = ['created_at']


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """For creating appointments from mobile"""
    patient_phone = serializers.CharField(write_only=True, required=False)
    patient_first_name = serializers.CharField(write_only=True, required=False)
    patient_last_name = serializers.CharField(write_only=True, required=False)
    dental_issue = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'service', 'appointment_date', 'appointment_time', 
                  'notes', 'patient_phone', 'patient_first_name', 'patient_last_name', 'dental_issue']
    
    def create(self, validated_data):
        # Handle new patient creation
        patient_phone = validated_data.pop('patient_phone', None)
        patient_first_name = validated_data.pop('patient_first_name', None)
        patient_last_name = validated_data.pop('patient_last_name', None)
        dental_issue = validated_data.pop('dental_issue', None)
        
        if patient_phone and not validated_data.get('patient'):
            # Try to find existing patient or create new
            from patients.models import Patient
            patient, created = Patient.objects.get_or_create(
                phone=patient_phone,
                defaults={
                    'first_name': patient_first_name or 'New',
                    'last_name': patient_last_name or 'Patient',
                    'reason_for_visit': dental_issue,
                    'is_active': True
                }
            )
            validated_data['patient'] = patient
        
        return super().create(validated_data)


# ==================== INVOICE SERIALIZERS ====================

class InvoiceSerializer(serializers.ModelSerializer):
    """Invoice information for mobile apps"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'patient', 'patient_name', 'issue_date', 
                  'total_amount', 'paid_amount', 'balance_due', 'status']


# ==================== AUTHENTICATION SERIALIZERS ====================

class LoginSerializer(serializers.Serializer):
    """Login request serializer"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile for mobile"""
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'full_name', 'phone', 'role', 'is_active']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()


# ==================== BOOKING REQUEST SERIALIZER ====================

class BookingRequestSerializer(serializers.ModelSerializer):
    """For public booking requests from mobile"""
    
    class Meta:
        from appointments.models import BookingRequest
        model = BookingRequest
        fields = ['first_name', 'last_name', 'phone', 'email', 'service_requested', 
                  'dental_issue', 'preferred_date', 'preferred_time']