"""
Django settings for Dental Clinic Management System
Configured for PostgreSQL on Railway
"""

from pathlib import Path
import os
import sys
import dj_database_url

# =======================
# PATH CONFIGURATION
# =======================

# Determine paths
if getattr(sys, 'frozen', False):
    # Running as EXE
    BASE_DIR = Path(sys._MEIPASS)
    DATA_DIR = Path(os.environ.get('DENTAL_CLINIC_DATA_DIR', Path(os.path.dirname(sys.executable)) / 'data'))
else:
    # Running as script
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / 'data'

# Create data directory (for media files and logs)
DATA_DIR.mkdir(exist_ok=True)

# =======================
# SECURITY & DEBUG - FIXED FOR RAILWAY
# =======================

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dental-clinic-standalone-key')

# ✅ FIX: Force DEBUG=True on Railway to prevent redirect loop
DEBUG = True  # Changed from False

# ✅ FIX: Allow all hosts
ALLOWED_HOSTS = ['*']

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'https://dorah-dental-production.up.railway.app',
    'https://*.railway.app',
    'https://*.up.railway.app',
    'http://*.railway.app',
    'http://*.up.railway.app',
]

# CORS settings for mobile apps
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# =======================
# INSTALLED APPS
# =======================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    
    # Third-party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    
    # Custom apps
    'patients',
    'appointments',
    'billing',
    'core',
    'inventory',
    'notifications',
    'patient_portal',
    'api',
    'reports',
]

# =======================
# MIDDLEWARE
# =======================

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dental_clinic.urls'
WSGI_APPLICATION = 'dental_clinic.wsgi.application'

# =======================
# DATABASE - PostgreSQL on Railway
# =======================

DATABASE_URL = "postgresql://postgres:yMgKMbELWuRVkvCumYxKoBzGgRmZHoJb@altaria.proxy.rlwy.net:15815/railway"

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

print("=" * 50)
print("🦷 DATABASE CONNECTION")
print("=" * 50)
print(f"Host: {DATABASES['default']['HOST']}")
print(f"Port: {DATABASES['default']['PORT']}")
print(f"Database: {DATABASES['default']['NAME']}")
print(f"User: {DATABASES['default']['USER']}")
print("=" * 50)

# =======================
# REST FRAMEWORK
# =======================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# =======================
# TEMPLATES
# =======================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.business_info',
            ],
        },
    },
]

# =======================
# STATIC & MEDIA FILES
# =======================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = DATA_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = DATA_DIR / 'media'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =======================
# AUTHENTICATION
# =======================

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# =======================
# CRISPY FORMS
# =======================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# =======================
# DEFAULT AUTO FIELD
# =======================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =======================
# BUSINESS INFO
# =======================

BUSINESS_NAME = "DORA'S DENTAL GEM"
BUSINESS_SHORT_NAME = "Dora's Dental Gem"
BUSINESS_TAGLINE = "Quality Dental Care"
BUSINESS_LOGO_ICON = "fa-tooth"
BUSINESS_LOGO_TEXT = "DORA'S"
BUSINESS_LOGO_HIGHLIGHT = "DENTAL"
BUSINESS_EMAIL = "info@dorasdentalgem.com"
BUSINESS_PHONE = "+256 700 000 000"
BUSINESS_ADDRESS = "Kampala, Uganda"
BUSINESS_CURRENCY = "UGX"
BUSINESS_YEAR = "2026"
BUSINESS_PRIMARY_COLOR = "#1a5276"
BUSINESS_SECONDARY_COLOR = "#2980b9"
BUSINESS_ACCENT_COLOR = "#2ecc71"
BUSINESS_DARK_COLOR = "#0a1a2e"
BUSINESS_CARD_COLOR = "#f8f9fa"
BUSINESS_MUTED_COLOR = "#6c757d"
BUSINESS_BORDER_COLOR = "#dee2e6"
BUSINESS_BADGES = ["Trusted", "Professional", "Caring"]

# =======================
# YOOLA SMS SETTINGS
# =======================

YOOLA_API_KEY = '97H826E9p99932TpN6A3WY631y6wvx7519Cc87vV75uM6v1NAf3LlR8xiYTipIIg'
YOOLA_SENDER_ID = 'YoolaSMS'

# =======================
# LOGGING
# =======================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {
            'class': 'logging.FileHandler',
            'filename': DATA_DIR / 'dental_clinic.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# =======================
# SECURITY SETTINGS - ✅ ALL DISABLED FOR RAILWAY
# =======================

# ✅ FIX: All security settings disabled to prevent redirect loop
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None
USE_X_FORWARDED_HOST = False
USE_X_FORWARDED_PORT = False

# =======================
# STARTUP MESSAGE
# =======================

print("=" * 50)
print("🦷 DENTAL CLINIC SYSTEM LOADED")
print("=" * 50)
print(f"Data Directory: {DATA_DIR}")
print(f"Database: {DATABASES['default']['NAME']}")
print(f"Database Engine: {DATABASES['default']['ENGINE']}")
print(f"DEBUG Mode: {DEBUG}")
print("=" * 50)