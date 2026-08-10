from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # OTP Verification
    path('otp-verify/', views.otp_verify_view, name='otp_verify'),
    path('otp-send/', views.otp_send_view, name='otp_send'),
    
    # Dashboards
    path('', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('receptionist-dashboard/', views.receptionist_dashboard, name='receptionist_dashboard'),
    path('accountant-dashboard/', views.accountant_dashboard, name='accountant_dashboard'),
    path('users/<int:pk>/reset-otp/', views.reset_user_otp, name='reset_user_otp'),
    # Revenue Reports
    path('revenue/', views.revenue_dashboard, name='revenue_dashboard'),
    path('company-settings/', views.company_settings, name='company_settings'),
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/activate/', views.user_activate, name='user_activate'),
    
    # Role Management
    path('roles/', views.role_management, name='role_management'),
]