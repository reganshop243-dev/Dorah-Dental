from django.contrib import admin
from .models import Invoice, InvoiceItem, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'patient_name', 'total_amount', 'status', 'issue_date']
    list_filter = ['status', 'payment_method', 'issue_date']
    search_fields = ['invoice_number', 'patient_name', 'patient_phone']
    readonly_fields = ['subtotal', 'tax_amount', 'total_amount', 'balance_due']
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'patient', 'appointment', 'patient_name', 'patient_phone')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'discount', 'total_amount', 'amount_paid', 'balance_due')
        }),
        ('Status & Payment', {
            'fields': ('status', 'payment_method', 'issue_date', 'due_date', 'payment_date')
        }),
        ('Additional Information', {
            'fields': ('reference_number', 'notes', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'description', 'quantity', 'unit_price', 'total_price']
    list_filter = ['invoice__status']
    search_fields = ['description', 'procedure_code']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'status', 'payment_date']
    list_filter = ['payment_method', 'status', 'payment_date']
    search_fields = ['transaction_id', 'reference']