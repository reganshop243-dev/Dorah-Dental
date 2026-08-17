from rest_framework import serializers
from .models import Invoice, InvoiceItem, Payment, Expense

class InvoiceItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    inventory_name = serializers.CharField(source='inventory_item.name', read_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = '__all__'

class InvoiceSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    status_display = serializers.SerializerMethodField()
    payment_method_display = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['invoice_number', 'created_at', 'updated_at']
    
    def get_status_display(self, obj):
        return dict(Invoice.STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_payment_method_display(self, obj):
        return dict(Invoice.PAYMENT_METHOD_CHOICES).get(obj.payment_method, obj.payment_method)

class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    patient_name = serializers.CharField(source='invoice.patient_name', read_only=True)
    status_display = serializers.SerializerMethodField()
    method_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = '__all__'
    
    def get_status_display(self, obj):
        return dict(Payment.PAYMENT_STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_method_display(self, obj):
        return dict(Invoice.PAYMENT_METHOD_CHOICES).get(obj.payment_method, obj.payment_method)

class ExpenseSerializer(serializers.ModelSerializer):
    category_display = serializers.SerializerMethodField()
    payment_method_display = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Expense
        fields = '__all__'
    
    def get_category_display(self, obj):
        return dict(Expense.EXPENSE_CATEGORIES).get(obj.category, obj.category)
    
    def get_payment_method_display(self, obj):
        return dict(Expense.PAYMENT_METHOD_CHOICES).get(obj.payment_method, obj.payment_method)
