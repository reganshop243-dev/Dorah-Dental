from django.test import TestCase
from .models import Invoice, Patient

class BillingModelTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(first_name='Jane', last_name='Smith', phone='+256700000001')
    
    def test_invoice_creation(self):
        invoice = Invoice.objects.create(
            invoice_number='INV-00001', patient=self.patient,
            patient_name='Jane Smith', patient_phone='+256700000001',
            subtotal=100000, total_amount=100000
        )
        self.assertEqual(invoice.invoice_number, 'INV-00001')
