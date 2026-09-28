from decimal import Decimal
from django.test import TestCase
from .models import Invoice, Patient, Payment

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


class InstallmentPaymentCompletionTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(first_name='Test', last_name='Patient')
        self.invoice = Invoice.objects.create(
            invoice_number='TEST-INST-001', patient=self.patient,
            patient_name=self.patient.full_name, patient_phone='',
            subtotal=100000, tax_rate=0, tax_amount=0, discount=0,
            total_amount=100000, amount_paid=0, balance_due=100000, status='sent'
        )

    def test_multiple_installments_complete_invoice(self):
        Payment.objects.create(invoice=self.invoice, amount=30000, payment_method='cash', status='completed')
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'partially_paid')
        self.assertEqual(self.invoice.balance_due, Decimal('70000.00'))

        Payment.objects.create(invoice=self.invoice, amount=70000, payment_method='cash', status='completed')
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')
        self.assertEqual(self.invoice.balance_due, Decimal('0.00'))
        self.assertEqual(self.invoice.amount_paid, Decimal('100000.00'))

    def test_failed_payment_does_not_complete_invoice(self):
        Payment.objects.create(invoice=self.invoice, amount=100000, payment_method='cash', status='failed')
        self.invoice.refresh_from_db()
        self.assertNotEqual(self.invoice.status, 'paid')
        self.assertEqual(self.invoice.balance_due, Decimal('100000.00'))
