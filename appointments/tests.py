from django.test import TestCase
from django.contrib.auth.models import User
from .models import Appointment, Doctor, Service, Patient

class AppointmentModelTest(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(name='Dr. Test', specialization='General')
        self.patient = Patient.objects.create(first_name='John', last_name='Doe', phone='+256700000000')
        self.service = Service.objects.create(name='Test Service', price=100000)
    
    def test_appointment_creation(self):
        appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, service=self.service,
            appointment_date='2026-08-20', appointment_time='10:00:00'
        )
        self.assertEqual(appointment.patient.first_name, 'John')
