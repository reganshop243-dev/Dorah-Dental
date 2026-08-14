

# Create your tests here.
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('aging/', views.aging_report, name='aging'),
    path('patient-visits/', views.patient_visits_report, name='patient_visits'),
    path('doctor-performance/', views.doctor_performance_report, name='doctor_performance'),
]