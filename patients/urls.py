from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.patient_list, name='list'),
    path('add/', views.patient_add, name='add'),
    path('<int:pk>/', views.patient_detail, name='detail'),
    path('<int:pk>/edit/', views.patient_edit, name='edit'),
    path('<int:pk>/delete/', views.patient_delete, name='delete'),
    path('api/search/', views.patient_search_api, name='search_api'),
    path('<int:pk>/add-image/', views.patient_add_image, name='add_image'),
    path('<int:pk>/dental-chart/', views.dental_chart, name='dental_chart'),
]