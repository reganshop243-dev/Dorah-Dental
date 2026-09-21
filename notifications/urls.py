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
    path('', views.notification_center, name='center'),
    path('<int:pk>/read/', views.notification_mark_read, name='mark_read'),
    path('mark-all-read/', views.notification_mark_all_read, name='mark_all_read'),
    path('push/subscribe/', views.push_subscribe, name='push_subscribe'),
    path('push/public-key/', views.push_public_key, name='push_public_key'),
    path('contact-access/<int:pk>/<str:decision>/', views.contact_access_decision, name='contact_access_decision'),
]
