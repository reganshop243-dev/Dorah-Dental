from django.contrib import admin
from .models import (
    PatientPortalAccess, PatientPortalLog, PortalOffer,
    PatientConversation, PatientMessage, PortalNotification,
)


@admin.register(PatientPortalAccess)
class PatientPortalAccessAdmin(admin.ModelAdmin):
    list_display = ['patient', 'is_active', 'last_login', 'is_locked']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__phone']
    list_filter = ['is_active']
    readonly_fields = ['last_login', 'login_attempts', 'locked_until', 'created_at', 'updated_at']


@admin.register(PatientPortalLog)
class PatientPortalLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'action', 'timestamp']
    search_fields = ['patient__first_name', 'patient__last_name', 'action']
    list_filter = ['action']
    readonly_fields = ['patient', 'action', 'ip_address', 'user_agent', 'timestamp']


@admin.register(PortalOffer)
class PortalOfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'valid_from', 'valid_until', 'is_published', 'created_at']
    list_filter = ['is_published', 'valid_from', 'valid_until']
    search_fields = ['title', 'description']
    list_editable = ['is_published']
    readonly_fields = ['created_at', 'updated_at']


class PatientMessageInline(admin.TabularInline):
    model = PatientMessage
    extra = 0
    fields = ['sender_type', 'sender', 'body', 'created_at', 'read_at']
    readonly_fields = ['created_at']


@admin.register(PatientConversation)
class PatientConversationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'subject', 'doctor', 'status', 'updated_at', 'unread_patient_messages']
    list_filter = ['status', 'doctor', 'updated_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__phone', 'subject']
    list_editable = ['status']
    inlines = [PatientMessageInline]
    readonly_fields = ['created_at', 'updated_at']

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, PatientMessage) and obj.sender_type == 'staff' and not obj.sender:
                obj.sender = request.user
            obj.save()
        formset.save_m2m()

    @admin.display(description='Unread patient messages')
    def unread_patient_messages(self, obj):
        return obj.messages.filter(sender_type='patient', read_at__isnull=True).count()


@admin.register(PatientMessage)
class PatientMessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'sender_type', 'sender', 'created_at', 'read_at']
    list_filter = ['sender_type', 'created_at']
    search_fields = ['conversation__patient__first_name', 'conversation__patient__last_name', 'body']
    readonly_fields = ['created_at']

    def save_model(self, request, obj, form, change):
        if obj.sender_type == 'staff' and not obj.sender:
            obj.sender = request.user
        super().save_model(request, obj, form, change)
        obj.conversation.save(update_fields=['updated_at'])


@admin.register(PortalNotification)
class PortalNotificationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'title', 'message']
    readonly_fields = ['created_at']
