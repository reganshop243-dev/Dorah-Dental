from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from .models import Invoice, Payment, Expense
from .serializers import InvoiceSerializer, PaymentSerializer, ExpenseSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().order_by('-issue_date')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        patient_id = self.request.query_params.get('patient')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        return queryset

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-expense_date')
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def revenue_stats(request):
    period = request.query_params.get('period', 'month')
    now = timezone.now()
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0)
    elif period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    else:  # month
        start_date = now - timedelta(days=30)
    
    invoices = Invoice.objects.filter(
        issue_date__gte=start_date,
        status='paid'
    )
    
    total_revenue = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    
    return Response({
        'period': period,
        'start_date': start_date,
        'end_date': now,
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'invoice_count': invoices.count(),
        'average_invoice': total_revenue / invoices.count() if invoices.count() > 0 else 0
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unpaid_invoices(request):
    invoices = Invoice.objects.filter(
        Q(status='draft') | Q(status='sent') | Q(status='partially_paid') | Q(status='overdue')
    ).order_by('-issue_date')
    serializer = InvoiceSerializer(invoices, many=True)
    return Response(serializer.data)
