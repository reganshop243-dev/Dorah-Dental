"""
Django settings for Dental Clinic Management System
Configured for PostgreSQL on Railway
"""

from pathlib import Path
import os
import sys
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

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

DEBUG = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-change-this-key-before-production'
    else:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG=False')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    'ALLOWED_HOSTS', 'localhost,127.0.0.1,dorah-dental-production.up.railway.app'
).split(',') if h.strip()]

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get(
    'CSRF_TRUSTED_ORIGINS', 'https://dorah-dental-production.up.railway.app'
).split(',') if o.strip()]

# Keep the API usable by an explicitly configured frontend/mobile origin.
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]
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
    'axes',
    
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
    'axes.middleware.AxesMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.OTPVerificationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dental_clinic.urls'
WSGI_APPLICATION = 'dental_clinic.wsgi.application'

# =======================
# DATABASE - PostgreSQL on Railway
# =======================

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG)}
else:
    # Local development fallback; production should use DATABASE_URL.
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }}

print("=" * 50)
print("🦷 DATABASE CONNECTION")
print(f"Database engine: {DATABASES['default'].get('ENGINE')}")
print(f"Database name: {DATABASES['default'].get('NAME')}")
print(f"Database host: {DATABASES['default'].get('HOST', '')}")
print("=" * 50)
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
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',
        'user': '1000/day',
    },
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

YOOLA_API_KEY = os.environ.get('YOOLA_API_KEY', '')
YOOLA_SENDER_ID = os.environ.get('YOOLA_SENDER_ID', 'YoolaSMS')

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
# PRODUCTION SECURITY
# =======================
SECURE_SSL_REDIRECT = (
    os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ('1', 'true', 'yes')
    and not DEBUG
)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000')) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Password hardening / brute-force protection (django-axes)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_LOCKOUT_CALLABLE = None

# =======================
# STARTUP MESSAGE
# =======================

print("=" * 50)
print("🦷 DENTAL CLINIC SYSTEM LOADED")
print("=" * 50)
print(f"Data Directory: {DATA_DIR}")
print(f"Database: {DATABASES['default'].get('NAME', '')}")
print(f"Database Engine: {DATABASES['default']['ENGINE']}")
print(f"DEBUG Mode: {DEBUG}")
print("=" * 50)