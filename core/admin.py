from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, CompanySettings

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['role', 'phone', 'address', 'profile_picture', 'doctor', 'phone_verified', 'is_active']

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'profile_role']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    def profile_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.role
        return 'None'
    profile_role.short_description = 'Role'

# Unregister default User admin and register custom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'phone_verified', 'is_active']
    list_filter = ['role', 'phone_verified', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone']

@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'phone', 'email', 'currency']
    fieldsets = (
        ('Business Info', {
            'fields': ('business_name', 'business_short_name', 'tagline', 'description')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'website', 'address')
        }),
        ('Social Media', {
            'fields': ('facebook', 'twitter', 'instagram', 'youtube')
        }),
        ('Business Hours', {
            'fields': ('monday_hours', 'tuesday_hours', 'wednesday_hours', 
                       'thursday_hours', 'friday_hours', 'saturday_hours', 'sunday_hours')
        }),
        ('Branding', {
            'fields': ('logo', 'favicon')
        }),
        ('Currency & Tax', {
            'fields': ('currency', 'currency_symbol', 'timezone', 'country', 'tax_rate', 'tax_id')
        }),
        ('Invoice Settings', {
            'fields': ('invoice_prefix', 'invoice_footer')
        }),
        ('Notification Settings', {
            'fields': ('notification_email', 'notification_phone')
        }),
    )
