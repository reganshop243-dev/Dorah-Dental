from rest_framework import serializers
from .models import Patient, DentalImage

class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='full_name', read_only=True)
    age = serializers.SerializerMethodField()
    age_display = serializers.CharField(source='age_display', read_only=True)
    gender_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ['registered_at']
    
    def get_age(self, obj):
        return obj.age
    
    def get_gender_display(self, obj):
        return dict(Patient.GENDER_CHOICES).get(obj.gender, obj.gender)

class DentalImageSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    image_type_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = DentalImage
        fields = '__all__'
        read_only_fields = ['uploaded_at']
    
    def get_image_type_display(self, obj):
        return dict(DentalImage.IMAGE_TYPES).get(obj.image_type, obj.image_type)
