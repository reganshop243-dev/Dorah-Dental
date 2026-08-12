from django.urls import path
from . import views

app_name = 'patient_portal'

urlpatterns = [
    # Authentication
    path('login/', views.patient_portal_login, name='login'),
    path('logout/', views.patient_portal_logout, name='logout'),
    
    # Dashboard and Profile
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_contact, name='update_contact'),
    
    # Appointments
    path('appointments/', views.appointments, name='appointments'),
    
    # Invoices
    path('invoices/', views.invoices, name='invoices'),
    
    # Services
    path('services/', views.services, name='services'),
    path('<int:pk>/generate-portal-pin/', views.generate_portal_pin, name='generate_portal_pin'),
    # Dental Images
    path('dental-images/', views.dental_images, name='dental_images'),
]