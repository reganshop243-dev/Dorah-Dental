from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'invoices', api_views.InvoiceViewSet)
router.register(r'payments', api_views.PaymentViewSet)
router.register(r'expenses', api_views.ExpenseViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('revenue/', api_views.revenue_stats, name='revenue_stats'),
    path('unpaid-invoices/', api_views.unpaid_invoices, name='unpaid_invoices'),
]
