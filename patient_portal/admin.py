

# Register your models here.
from django.contrib import admin
from .models import PatientPortalAccess, PatientPortalLog

@admin.register(PatientPortalAccess)
class PatientPortalAccessAdmin(admin.ModelAdmin):
    list_display = ['patient', 'portal_pin', 'is_active', 'last_login', 'is_locked']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__phone']
    list_filter = ['is_active']
    readonly_fields = ['last_login', 'login_attempts', 'locked_until']

@admin.register(PatientPortalLog)
class PatientPortalLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'action', 'timestamp']
    search_fields = ['patient__first_name', 'patient__last_name', 'action']
    list_filter = ['action']
    readonly_fields = ['patient', 'action', 'ip_address', 'user_agent', 'timestamp']