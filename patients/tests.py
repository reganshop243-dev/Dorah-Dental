from django.test import TestCase
from .models import Patient

class PatientModelTest(TestCase):
    def test_patient_creation(self):
        patient = Patient.objects.create(
            first_name='Alice', last_name='Johnson', phone='+256700000002', gender='F'
        )
        self.assertEqual(patient.full_name, 'Alice Johnson')
