from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # ==================== PUBLIC ENDPOINTS ====================
    path('services/', views.PublicServiceListView.as_view(), name='public_services'),
    path('doctors/', views.PublicDoctorListView.as_view(), name='public_doctors'),
    path('book/', views.PublicBookAppointmentView.as_view(), name='public_book'),
    path('booking-request/', views.PublicBookingRequestView.as_view(), name='public_booking_request'),
    
    # ==================== AUTHENTICATION ====================
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # ==================== PATIENT ENDPOINTS ====================
    path('patient/profile/', views.PatientProfileView.as_view(), name='patient_profile'),
    path('patient/appointments/', views.PatientAppointmentsView.as_view(), name='patient_appointments'),
    path('patient/appointments/create/', views.PatientAppointmentCreateView.as_view(), name='patient_appointment_create'),
    path('patient/invoices/', views.PatientInvoicesView.as_view(), name='patient_invoices'),
    
    # ==================== ADMIN/STAFF ENDPOINTS ====================
    path('admin/appointments/', views.AllAppointmentsView.as_view(), name='admin_appointments'),
    path('admin/patients/', views.AllPatientsView.as_view(), name='admin_patients'),
    path('admin/stats/', views.DashboardStatsView.as_view(), name='admin_stats'),
]