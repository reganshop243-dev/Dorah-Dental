from django.contrib import admin
from .models import NotificationSetting, NotificationLog

@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ['enable_reminders', 'reminder_hours_before', 'channel']
    fieldsets = (
        ('General Settings', {
            'fields': ('enable_reminders', 'reminder_hours_before', 'channel')
        }),
        ('Email Settings', {
            'fields': ('email_subject', 'email_template')
        }),
        ('SMS Settings', {
            'fields': ('sms_template', 'twilio_account_sid', 'twilio_auth_token', 'twilio_phone_number')
        }),
    )

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'channel', 'sent_to', 'status', 'sent_at', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'sent_to']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
