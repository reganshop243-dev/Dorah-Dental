from django.conf import settings

def business_info(request):
    return {
        'business_name': getattr(settings, 'BUSINESS_NAME', 'Tusakimu Dental Clinic'),
        'business_short_name': getattr(settings, 'BUSINESS_SHORT_NAME', 'Tusakimu Dental'),
        'business_tagline': getattr(settings, 'BUSINESS_TAGLINE', 'Quality Dental Care'),
        'business_logo_icon': getattr(settings, 'BUSINESS_LOGO_ICON', 'fa-tooth'),
        'business_logo_text': getattr(settings, 'BUSINESS_LOGO_TEXT', 'TUSAKIMU'),
        'business_logo_highlight': getattr(settings, 'BUSINESS_LOGO_HIGHLIGHT', 'DENTAL'),
        'business_email': getattr(settings, 'BUSINESS_EMAIL', 'info@tusakimu.com'),
        'business_phone': getattr(settings, 'BUSINESS_PHONE', '+256 700 000 000'),
        'business_address': getattr(settings, 'BUSINESS_ADDRESS', 'Kampala, Uganda'),
        'business_currency': getattr(settings, 'BUSINESS_CURRENCY', 'UGX'),
        'business_year': getattr(settings, 'BUSINESS_YEAR', '2026'),
        'business_primary_color': getattr(settings, 'BUSINESS_PRIMARY_COLOR', '#1a5276'),
        'business_secondary_color': getattr(settings, 'BUSINESS_SECONDARY_COLOR', '#2980b9'),
        'business_accent_color': getattr(settings, 'BUSINESS_ACCENT_COLOR', '#2ecc71'),
        'business_dark_color': getattr(settings, 'BUSINESS_DARK_COLOR', '#0a1a2e'),
        'business_card_color': getattr(settings, 'BUSINESS_CARD_COLOR', '#f8f9fa'),
        'business_muted_color': getattr(settings, 'BUSINESS_MUTED_COLOR', '#6c757d'),
        'business_border_color': getattr(settings, 'BUSINESS_BORDER_COLOR', '#dee2e6'),
        'business_badges': getattr(settings, 'BUSINESS_BADGES', ['Trusted', 'Professional', 'Caring']),
        'business_colors': {
            'primary': getattr(settings, 'BUSINESS_PRIMARY_COLOR', '#1a5276'),
            'secondary': getattr(settings, 'BUSINESS_SECONDARY_COLOR', '#2980b9'),
            'accent': getattr(settings, 'BUSINESS_ACCENT_COLOR', '#2ecc71'),
            'dark': getattr(settings, 'BUSINESS_DARK_COLOR', '#0a1a2e'),
            'card': getattr(settings, 'BUSINESS_CARD_COLOR', '#f8f9fa'),
            'muted': getattr(settings, 'BUSINESS_MUTED_COLOR', '#6c757d'),
            'border': getattr(settings, 'BUSINESS_BORDER_COLOR', '#dee2e6'),
        }
    }


from django.contrib.auth.models import User

def user_role(request):
    """Add user role to template context"""
    context = {}
    if request.user.is_authenticated:
        try:
            context['user_role'] = request.user.profile.role
            context['user_role_display'] = request.user.profile.get_role_display()
        except:
            context['user_role'] = None
            context['user_role_display'] = None
    else:
        context['user_role'] = None
        context['user_role_display'] = None
    return context

from django.conf import settings
from core.models import CompanySettings

def business_info(request):
    """Add business information to all templates"""
    # Get company settings from database
    try:
        company = CompanySettings.get_settings()
    except:
        # Fallback to settings if database doesn't have company settings yet
        company = None
    
    return {
        # From database (if available)
        'company': company,
        
        # From settings (fallback)
        'business_name': getattr(settings, 'BUSINESS_NAME', "Dora's Dental Gem"),
        'business_short_name': getattr(settings, 'BUSINESS_SHORT_NAME', "Dora's Dental"),
        'business_tagline': getattr(settings, 'BUSINESS_TAGLINE', "Quality Dental Care"),
        'business_logo_icon': getattr(settings, 'BUSINESS_LOGO_ICON', "fa-gem"),
        'business_logo_text': getattr(settings, 'BUSINESS_LOGO_TEXT', "Dora's Dental"),
        'business_logo_highlight': getattr(settings, 'BUSINESS_LOGO_HIGHLIGHT', "Gem"),
        'business_email': getattr(settings, 'BUSINESS_EMAIL', "info@dorasdentalgem.com"),
        'business_phone': getattr(settings, 'BUSINESS_PHONE', "+256 700 000 000"),
        'business_address': getattr(settings, 'BUSINESS_ADDRESS', "Kampala, Uganda"),
        'business_currency': getattr(settings, 'BUSINESS_CURRENCY', "UGX"),
        'business_year': getattr(settings, 'BUSINESS_YEAR', "2026"),
        'business_primary_color': getattr(settings, 'BUSINESS_PRIMARY_COLOR', "#1a5276"),
        'business_secondary_color': getattr(settings, 'BUSINESS_SECONDARY_COLOR', "#2980b9"),
        'business_accent_color': getattr(settings, 'BUSINESS_ACCENT_COLOR', "#2ecc71"),
        'business_dark_color': getattr(settings, 'BUSINESS_DARK_COLOR', "#0a1a2e"),
        'business_card_color': getattr(settings, 'BUSINESS_CARD_COLOR', "#f8f9fa"),
        'business_muted_color': getattr(settings, 'BUSINESS_MUTED_COLOR', "#6c757d"),
        'business_border_color': getattr(settings, 'BUSINESS_BORDER_COLOR', "#dee2e6"),
        'business_badges': getattr(settings, 'BUSINESS_BADGES', ["Trusted", "Professional", "Caring"]),
    }



