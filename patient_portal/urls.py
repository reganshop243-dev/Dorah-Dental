from django.urls import path
from . import views
from patients.views import generate_portal_pin

app_name = 'patient_portal'

urlpatterns = [
    path('login/', views.patient_portal_login, name='login'),
    path('logout/', views.patient_portal_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_contact, name='update_contact'),
    path('appointments/', views.appointments, name='appointments'),
    path('services/', views.services, name='services'),
    path('<int:pk>/generate-portal-pin/', generate_portal_pin, name='generate_portal_pin'),
    path('dental-images/', views.dental_images, name='dental_images'),
]