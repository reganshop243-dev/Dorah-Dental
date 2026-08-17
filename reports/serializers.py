from rest_framework import serializers
from django.db.models import Sum, Count
from billing.models import Invoice
from appointments.models import Appointment, Doctor
from patients.models import Patient

class AgingReportSerializer(serializers.Serializer):
    patient_name = serializers.CharField()
    invoice_number = serializers.CharField()
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    age_days = serializers.IntegerField()
    aging_category = serializers.CharField()

class PatientVisitSerializer(serializers.Serializer):
    patient_name = serializers.CharField()
    total_visits = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_visit = serializers.DateField()
    first_visit = serializers.DateField()

class DoctorPerformanceSerializer(serializers.Serializer):
    doctor_name = serializers.CharField()
    total_appointments = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_per_patient = serializers.DecimalField(max_digits=12, decimal_places=2)
