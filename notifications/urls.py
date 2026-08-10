from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('settings/', views.notification_settings, name='settings'),
    path('test-reminder/', views.send_test_reminder, name='test_reminder'),
    path('test-reminder/', views.send_test_reminder, name='test_reminder'),
    path('test-email/', views.send_test_email, name='test_email'),
    path('test-sms/', views.send_test_sms, name='test_sms'),
    path('test-yoola/', views.test_yoola_sms, name='test_yoola'),  
    path('upcoming-reminders/', views.send_upcoming_reminders, name='upcoming_reminders'),
path('send-single-reminder/<int:pk>/', views.send_single_reminder, name='send_single_reminder'),
]
