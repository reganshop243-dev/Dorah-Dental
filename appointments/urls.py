from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Appointments
    path('appointments/', views.appointment_list, name='list'),
    path('appointments/add/', views.appointment_add, name='add'),
    path('appointments/<int:pk>/', views.appointment_detail, name='detail'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='edit'),
    path('appointments/<int:pk>/delete/', views.appointment_delete, name='delete'),
    path('appointments/calendar/', views.calendar_view, name='calendar'),
    path('api/services/search/', views.services_search_api, name='services_search_api'),
    # Services
    path('services/', views.service_list, name='services'),
    path('services/add/', views.service_add, name='service_add'),
    path('services/<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('services/<int:pk>/delete/', views.service_delete, name='service_delete'),
    
    # Doctors
    path('doctors/', views.doctor_list, name='doctors'),
    path('doctors/add/', views.doctor_add, name='doctor_add'),
    path('doctors/<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),
    path('doctors/<int:pk>/delete/', views.doctor_delete, name='doctor_delete'),
    path('<int:pk>/add-note/', views.add_clinical_note, name='add_clinical_note'),
    path('note/<int:pk>/delete/', views.delete_clinical_note, name='delete_clinical_note'),
]