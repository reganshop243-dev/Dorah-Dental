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
# SECURITY & DEBUG
# =======================

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dental-clinic-standalone-key')

# Debug mode - False on Railway, True locally
if os.environ.get('RAILWAY_ENVIRONMENT'):
    DEBUG = False
else:
    DEBUG = True

# Allowed hosts
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        '.railway.app',
        '.up.railway.app',
        os.environ.get('RAILWAY_PUBLIC_DOMAIN', ''),
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
    'crispy_forms',
    'crispy_bootstrap5',
    'patients',
    'appointments',
    'billing',
    'core',
    'inventory', 
    'notifications',
]

# =======================
# MIDDLEWARE
# =======================

MIDDLEWARE = [
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
# DATABASE - PostgreSQL ONLY (Railway)
# =======================

# =======================
# DATABASE - PostgreSQL (Railway)
# =======================

import dj_database_url

# Your actual Railway PostgreSQL connection string
DATABASE_URL = "postgresql://postgres:yMgKMbELWuRVkvCumYxKoBzGgRmZHoJb@altaria.proxy.rlwy.net:15815/railway"

# Use the DATABASE_URL
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

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =======================
# AUTHENTICATION
# =======================

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
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

# Colors - Clean Professional
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
# SECURITY SETTINGS (Production)
# =======================

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# =======================
# STARTUP MESSAGE
# =======================

print("=" * 50)
print("🦷 DENTAL CLINIC SYSTEM LOADED")
print("=" * 50)
print(f"Data Directory: {DATA_DIR}")
print(f"Database: {DATABASES['default']['NAME']}")
print(f"Database Engine: {DATABASES['default']['ENGINE']}")
print("=" * 50)