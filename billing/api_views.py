from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from core.permissions import is_financial_staff

class IsFinancialStaff(BasePermission):
    message = "Financial API access is restricted to administrators and accountants."
    action_permissions = {
        'list': 'billing.view', 'retrieve': 'billing.view',
        'create': 'billing.create', 'update': 'billing.edit', 'partial_update': 'billing.edit',
        'destroy': 'billing.delete',
    }
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and is_financial_staff(request.user)):
            return False
        code = self.action_permissions.get(getattr(view, 'action', None))
        return not code or request.user.profile.has_permission(code)

class PaymentPermission(IsFinancialStaff):
    action_permissions = {
        'list': 'billing.payments.view', 'retrieve': 'billing.payments.view',
        'create': 'billing.payments.create', 'update': 'billing.payments.edit', 'partial_update': 'billing.payments.edit',
        'destroy': 'billing.payments.delete',
    }

class ExpensePermission(IsFinancialStaff):
    action_permissions = {
        'list': 'billing.expenses.view', 'retrieve': 'billing.expenses.view',
        'create': 'billing.expenses.create', 'update': 'billing.expenses.edit', 'partial_update': 'billing.expenses.edit',
        'destroy': 'billing.expenses.delete',
    }

class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsFinancialStaff]
    queryset = Invoice.objects.all().order_by('-issue_date')
    serializer_class = InvoiceSerializer
    
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
    permission_classes = [PaymentPermission]
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = PaymentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            queryset = queryset.filter(invoice_id=invoice_id)
        return queryset

class ExpenseViewSet(viewsets.ModelViewSet):
    permission_classes = [ExpensePermission]
    queryset = Expense.objects.all().order_by('-expense_date')
    serializer_class = ExpenseSerializer

@api_view(['GET'])
@permission_classes([IsFinancialStaff])
def revenue_stats(request):
    if not request.user.profile.has_permission('reports.revenue'):
        return Response({'detail': 'Report permission required.'}, status=status.HTTP_403_FORBIDDEN)
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
@permission_classes([IsFinancialStaff])
def unpaid_invoices(request):
    if not request.user.profile.has_permission('billing.view'):
        return Response({'detail': 'Billing permission required.'}, status=status.HTTP_403_FORBIDDEN)
    invoices = Invoice.objects.filter(
        Q(status='draft') | Q(status='sent') | Q(status='partially_paid') | Q(status='overdue')
    ).order_by('-issue_date')
    serializer = InvoiceSerializer(invoices, many=True)
    return Response(serializer.data)
