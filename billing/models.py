from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from patients.models import Patient
from appointments.models import Appointment, Service, Doctor
from datetime import date


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('overdue', 'Overdue'),
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
    
    def save(self, *args, **kwargs):
        # Auto-calculate totals if not provided
        if self.subtotal and self.tax_rate is not None:
            self.tax_amount = (self.subtotal * self.tax_rate) / 100
            self.total_amount = self.subtotal + self.tax_amount - self.discount
        self.balance_due = self.total_amount - self.amount_paid
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
        # If payment_date is not set, use today
        if not self.payment_date:
            self.payment_date = date.today()
        super().save(*args, **kwargs)
        # Update invoice amount paid
        self.invoice.amount_paid = self.invoice.payments.filter(status='completed').aggregate(
            models.Sum('amount')
        )['amount__sum'] or 0
        self.invoice.save()


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