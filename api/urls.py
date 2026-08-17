from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from . import views
from .views import simple_stats_direct

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'patients', views.PatientViewSet, basename='patient')

app_name = 'api'

urlpatterns = [
    # ==================== API ROUTER ====================
    path('', include(router.urls)),
    
    # ==================== PUBLIC ENDPOINTS ====================
    path('services/', views.ServiceListView.as_view(), name='services'),
    path('doctors/', views.DoctorListView.as_view(), name='doctors'),
    path('book/', views.PublicBookAppointmentView.as_view(), name='public_book'),
    path('booking-request/', views.PublicBookingRequestView.as_view(), name='public_booking_request'),
    
    # ==================== AUTHENTICATION ====================
    path('login/', csrf_exempt(views.LoginView.as_view()), name='login'),
    
    # ==================== PATIENT ENDPOINTS ====================
    path('patient/profile/', views.PatientProfileView.as_view(), name='patient_profile'),
    path('patient/appointments/', views.PatientAppointmentsView.as_view(), name='patient_appointments'),
    path('patient/appointments/create/', views.PatientAppointmentCreateView.as_view(), name='patient_appointment_create'),
    path('patient/invoices/', views.PatientInvoicesView.as_view(), name='patient_invoices'),
    
    # ==================== APPOINTMENT ENDPOINTS ====================
    path('appointments/', views.AppointmentListView.as_view(), name='appointments'),
    
    # ==================== BILLING ENDPOINTS ====================
    path('invoices/', views.InvoiceListView.as_view(), name='invoices'),
    path('billing/balance-sheet/', views.BalanceSheetView.as_view(), name='balance_sheet'),
    
    # ==================== INVENTORY ENDPOINTS ====================
    path('inventory/', views.InventoryListView.as_view(), name='inventory'),
    
    # ==================== SETTINGS ENDPOINTS ====================
    path('settings/', views.SettingsView.as_view(), name='settings'),
    
    # ==================== REPORTS ENDPOINTS ====================
    path('reports/aging/', views.AgingReportView.as_view(), name='aging_report'),
    path('reports/patient-visits/', views.PatientVisitsView.as_view(), name='patient_visits'),
    path('reports/doctor-performance/', views.DoctorPerformanceView.as_view(), name='doctor_performance'),
    
    # ==================== ADMIN/STAFF ENDPOINTS ====================
    path('admin/appointments/', views.AllAppointmentsView.as_view(), name='admin_appointments'),
    path('admin/patients/', views.AllPatientsView.as_view(), name='admin_patients'),
    path('admin/stats/', views.DashboardStatsView.as_view(), name='admin_stats'),
    path('balance-sheet/', views.BalanceSheetView.as_view(), name='balance-sheet'),
    path('revenue-dashboard/', views.RevenueDashboardView.as_view(), name='revenue-dashboard'),
    
    # ==================== STATS ====================
    path('stats/', simple_stats_direct, name='stats'),
    
    # ==================== REVENUE ====================
    path('core/revenue/', views.RevenueDashboardView.as_view(), name='revenue'),
    path('debug/app/', views.DebugAppView.as_view(), name='debug-app'),
]
