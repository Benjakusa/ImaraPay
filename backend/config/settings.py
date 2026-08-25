import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps folder to sys.path
sys.path.insert(0, str(BASE_DIR))

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-imara-pay-kenya-orchestration-secret-key-2026')

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'corsheaders',

    # Local Imara Pay apps — v2
    'apps.tenants',
    'apps.merchants',
    'apps.payments',
    'apps.webhooks',
    'apps.providers',
    'apps.whatsapp',
    'apps.audit',
    'apps.api',

    # v3 — WhatsApp-first additions
    'apps.identity',       # PhoneIdentity, StepUpChallenge, MagicLinkToken
    'apps.conversation',   # ConversationSession, command parser, handlers
    'apps.settings_web',   # Staff management, settlement settings, audit log
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.tenants.middleware.TenantMiddleware',
]

# CSRF exemptions for webhooks (Meta and PSP post without CSRF tokens)
CSRF_TRUSTED_ORIGINS = [
    'https://graph.facebook.com',
    'https://*.safaricom.co.ke',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PostgreSQL support for production ready databases
if os.environ.get('DATABASE_URL'):
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    except ImportError:
        pass
elif os.environ.get('DB_NAME'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'apps.api.authentication.BearerTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ── Celery / Redis ────────────────────────────────────────────────────────────
_REDIS_URL = os.environ.get('REDIS_URL', '')

if _REDIS_URL:
    # Production / staging: use Redis for broker and result backend
    CELERY_BROKER_URL = _REDIS_URL
    CELERY_RESULT_BACKEND = _REDIS_URL
    CELERY_TASK_ALWAYS_EAGER = False
else:
    # Development without Redis: tasks run synchronously inline (no broker needed)
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
    CELERY_TASK_ALWAYS_EAGER = True       # tasks run synchronously
    CELERY_TASK_EAGER_PROPAGATES = True   # exceptions propagate normally

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'

# Beat schedule — all expiry/reconciliation tasks
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'expire-payment-requests': {
        'task': 'payments.expire_payment_requests',
        'schedule': 60.0,  # every minute
    },
    'expire-conversation-sessions': {
        'task': 'conversation.expire_sessions',
        'schedule': 60.0,
    },
    'expire-step-up-challenges': {
        'task': 'identity.expire_step_up_challenges',
        'schedule': 60.0,
    },
    'expire-magic-link-tokens': {
        'task': 'identity.expire_magic_link_tokens',
        'schedule': 300.0,  # every 5 minutes
    },
}

# ── Imara Pay config ──────────────────────────────────────────────────────────
IMARA_PAY = {
    'BASE_URL': os.environ.get('FRONTEND_URL', 'http://localhost:5173'),
    'DEFAULT_CURRENCY': 'KES',
    'PROVIDER_DEFAULT': 'MPESA_SANDBOX',

    # WhatsApp Cloud API credentials (set via environment for production)
    'WHATSAPP_PHONE_NUMBER_ID': os.environ.get('WHATSAPP_PHONE_NUMBER_ID', ''),
    'WHATSAPP_ACCESS_TOKEN': os.environ.get('WHATSAPP_ACCESS_TOKEN', ''),
    'WHATSAPP_VERIFY_TOKEN': os.environ.get('WHATSAPP_VERIFY_TOKEN', 'imara-dev-verify'),
    'WHATSAPP_APP_SECRET': os.environ.get('WHATSAPP_APP_SECRET', ''),

    # Step-up auth (§7.4)
    'STEP_UP_EXPIRY_MINUTES': int(os.environ.get('STEP_UP_EXPIRY_MINUTES', '5')),
    'MAGIC_LINK_EXPIRY_HOURS': int(os.environ.get('MAGIC_LINK_EXPIRY_HOURS', '24')),
    'REPORT_LINK_EXPIRY_HOURS': int(os.environ.get('REPORT_LINK_EXPIRY_HOURS', '24')),

    # Confirmation threshold — amounts at or above this get an interactive confirm prompt (§8.2)
    # Default: KES 1,000 (amount_minor = 1000 since we store in shillings for MVP)
    'CONFIRMATION_THRESHOLD_MINOR': int(os.environ.get('CONFIRMATION_THRESHOLD_MINOR', '1000')),
}

# Convenience: expose keys used in services.py at module level too
STEP_UP_EXPIRY_MINUTES = IMARA_PAY['STEP_UP_EXPIRY_MINUTES']
MAGIC_LINK_EXPIRY_HOURS = IMARA_PAY['MAGIC_LINK_EXPIRY_HOURS']
REPORT_LINK_EXPIRY_HOURS = IMARA_PAY['REPORT_LINK_EXPIRY_HOURS']

