from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from patients.models import Patient
from appointments.models import Appointment, Service, Doctor
from datetime import date
from decimal import Decimal


class Invoice(models.Model):
    INVOICE_TYPE_CHOICES = [
        ('invoice', 'Normal Invoice'),
        ('booking', 'Booking'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('insurance', 'Insurance'),
        ('card', 'Card'),
        ('other', 'Other'),
    ]
    
    # Increased length limits for POS system
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='invoices')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    
    # Patient details snapshot (in case patient info changes later)
    patient_name = models.CharField(max_length=255)
    patient_phone = models.CharField(max_length=50)
    
    # ✅ FIX: Changed DateTimeField to DateField to avoid timezone warnings
    issue_date = models.DateField(default=date.today)  # Changed from DateTimeField
    due_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)  # Changed from DateTimeField
    
    # Financial fields with proper decimal places
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Status and metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES, default='invoice', db_index=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Extended fields for POS
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.CharField(max_length=150, blank=True, null=True)
    updated_by = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['issue_date']),
        ]
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.patient_name}"
    
    def sync_payment_state(self, payment_date=None):
        """Synchronize invoice balance/status from completed payments.

        An invoice is outstanding only while balance_due is positive. Any
        number of installments may be used; once completed payments reach the
        invoice total, the invoice becomes paid and its balance is exactly 0.
        """
        completed_paid = self.payments.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        self.amount_paid = max(Decimal(completed_paid), Decimal('0.00'))
        total = Decimal(self.total_amount or 0)
        self.balance_due = max(total - self.amount_paid, Decimal('0.00'))

        # A booking remains BOOKED even after payment. This allows staff to
        # distinguish money received for a future visit from a completed visit.
        if self.invoice_type == 'booking' and self.status != 'cancelled':
            self.status = 'booked'
            if self.amount_paid > 0 and payment_date:
                self.payment_date = payment_date
            return

        if total > 0 and self.balance_due <= 0:
            self.balance_due = Decimal('0.00')
            self.status = 'paid'
            if payment_date:
                self.payment_date = payment_date
            elif not self.payment_date:
                self.payment_date = date.today()
        elif self.amount_paid > 0 and self.balance_due > 0:
            self.status = 'partially_paid'
            self.payment_date = None

    def save(self, *args, **kwargs):
        # Auto-calculate totals if not provided
        if self.subtotal and self.tax_rate is not None:
            self.tax_amount = (self.subtotal * self.tax_rate) / 100
            self.total_amount = self.subtotal + self.tax_amount - self.discount
        self.balance_due = max(Decimal(self.total_amount or 0) - Decimal(self.amount_paid or 0), Decimal('0.00'))
        # Booking invoices stay BOOKED until staff deliberately changes the
        # invoice type to a normal invoice/completes the visit.
        if self.invoice_type == 'booking' and self.status != 'cancelled':
            self.status = 'booked'
        # Never leave a paid invoice marked as partially paid/overdue.
        elif self.total_amount and self.balance_due <= 0 and self.status not in ('cancelled', 'draft'):
            self.balance_due = Decimal('0.00')
            self.status = 'paid'
        elif self.amount_paid and self.balance_due > 0 and self.status not in ('cancelled', 'draft'):
            self.status = 'partially_paid'
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    inventory_item = models.ForeignKey('inventory.InventoryItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_items')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    tooth_number = models.CharField(max_length=10, blank=True, null=True)
    procedure_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.description} - {self.quantity} x {self.unit_price}"
    
    def save(self, *args, **kwargs):
        # Only calculate total price, nothing else
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=date.today)  # Changed from DateTimeField
    payment_method = models.CharField(max_length=50, choices=Invoice.PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    processed_by = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment {self.id} - {self.invoice.invoice_number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.payment_date:
            self.payment_date = date.today()
        super().save(*args, **kwargs)
        # Recalculate from all completed installments, then synchronize status.
        self.invoice.sync_payment_state(payment_date=self.payment_date if self.status == 'completed' else None)
        self.invoice.save()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        result = super().delete(*args, **kwargs)
        invoice.sync_payment_state()
        invoice.save()
        return result


class Expense(models.Model):
    EXPENSE_CATEGORIES = [
        ('rent', 'Rent'),
        ('utilities', 'Utilities'),
        ('salary', 'Salaries'),
        ('supplies', 'Dental Supplies'),
        ('equipment', 'Equipment'),
        ('maintenance', 'Maintenance'),
        ('marketing', 'Marketing'),
        ('insurance', 'Insurance'),
        ('tax', 'Taxes'),
        ('software', 'Software/IT'),
        ('training', 'Training'),
        ('travel', 'Travel'),
        ('other', 'Other'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=date.today)  # Changed from DateTimeField
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    receipt = models.FileField(upload_to='expenses/receipts/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expense_date']
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
    
    def __str__(self):
        return f"{self.get_category_display()} - UGX {self.amount} - {self.expense_date}"