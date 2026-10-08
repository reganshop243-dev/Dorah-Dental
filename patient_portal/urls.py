from django.urls import path
from . import views
from patients.views import generate_portal_pin

app_name = 'patient_portal'

urlpatterns = [
    path('app/', views.app_download, name='app_download'),
    path('login/', views.patient_portal_login, name='login'),
    path('logout/', views.patient_portal_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_contact, name='update_contact'),
    path('appointments/', views.appointments, name='appointments'),
    path('invoices/', views.invoices, name='invoices'),
    path('payments/', views.payments, name='payments'),
    path('treatment-history/', views.treatment_history, name='treatment_history'),
    path('services/', views.services, name='services'),
    path('offers/', views.offers, name='offers'),
    path('dental-tips/', views.dental_tips, name='dental_tips'),
    path('manage-content/', views.portal_content, name='portal_content'),
    path('manage-content/tips/add/', views.portal_tip_add, name='portal_tip_add'),
    path('manage-content/tips/<int:pk>/edit/', views.portal_tip_edit, name='portal_tip_edit'),
    path('manage-content/tips/<int:pk>/delete/', views.portal_tip_delete, name='portal_tip_delete'),
    path('manage-content/offers/add/', views.portal_offer_add, name='portal_offer_add'),
    path('manage-content/offers/<int:pk>/edit/', views.portal_offer_edit, name='portal_offer_edit'),
    path('manage-content/offers/<int:pk>/delete/', views.portal_offer_delete, name='portal_offer_delete'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.notification_read, name='notification_read'),
    path('notifications/read-all/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('messages/', views.messages_list, name='messages'),
    path('messages/new/', views.message_new, name='message_new'),
    path('messages/<int:pk>/', views.conversation, name='conversation'),
    path('staff/messages/', views.staff_messages, name='staff_messages'),
    path('staff/messages/<int:pk>/', views.staff_conversation, name='staff_conversation'),
    path('<int:pk>/generate-portal-pin/', generate_portal_pin, name='generate_portal_pin'),
    path('dental-images/', views.dental_images, name='dental_images'),
]
