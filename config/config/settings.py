import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"Environment variable '{name}' is required but not set.")
    return value


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or require_env('DJANGO_SECRET_KEY')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',') if os.environ.get('ALLOWED_HOSTS') else []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'core',
    'users',
    'clinic',
    'lab',
    'audit',
    'billing',
    'patient_flow',
    'notifications',
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
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_testing = 'test' in sys.argv

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_clinic_backend' if _testing else os.environ.get('DB_NAME', 'postgres'),
        'USER': 'postgres' if _testing else require_env('DB_USER'),
        'PASSWORD': 'testpass123' if _testing else require_env('DB_PASSWORD'),
        'HOST': 'localhost' if _testing else require_env('DB_HOST'),
        'PORT': '15432' if _testing else os.environ.get('DB_PORT', '6543'),
        'TEST': {
            'NAME': 'test_clinic_backend',
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.SupabaseJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# Required in production; in DEBUG mode the server still starts so you can test other things,
# but all authenticated endpoints will reject tokens until this is set.
# Find it at: Supabase dashboard → Settings → API → JWT Secret
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET', '')
if not SUPABASE_JWT_SECRET and not DEBUG:
    raise ImproperlyConfigured("Environment variable 'SUPABASE_JWT_SECRET' is required in production.")

# CORS — tighten CORS_ALLOWED_ORIGINS in production
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []

# Queue / patient flow settings (override via environment variables)
QUEUE_GRACE_PERIOD_MINUTES = int(os.environ.get('QUEUE_GRACE_PERIOD_MINUTES', 15))
QUEUE_CALL_TIMEOUT_MINUTES = int(os.environ.get('QUEUE_CALL_TIMEOUT_MINUTES', 5))

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Use a custom runner that temporarily marks managed=False models as managed
# so Django can create their tables in the test database.
TEST_RUNNER = 'tests.runner.UnmanagedModelTestRunner'

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL        = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TASK_ALWAYS_EAGER = _testing   # run tasks synchronously during tests
