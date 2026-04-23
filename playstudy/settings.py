"""
PlayStudy Django Settings
Secure, production-ready configuration.
"""
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ─────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-in-production')
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')

ALLOWED_HOSTS = ['*'] if DEBUG else os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# ─── Application Definition ──────────────────────────────
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
    # Local apps
    'accounts',
    'study',
    'folders',
    'games',
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

ROOT_URLCONF = 'playstudy.urls'

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

WSGI_APPLICATION = 'playstudy.wsgi.application'

# ─── Database ─────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///./playstudy_dev.db')

if DATABASE_URL.startswith('postgresql'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': DATABASE_URL.split('/')[-1].split('?')[0],
            'USER': DATABASE_URL.split('://')[1].split(':')[0],
            'PASSWORD': DATABASE_URL.split(':')[2].split('@')[0],
            'HOST': DATABASE_URL.split('@')[1].split(':')[0].split('/')[0],
            'PORT': DATABASE_URL.split('@')[1].split(':')[1].split('/')[0] if ':' in DATABASE_URL.split('@')[1] else '5432',
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }
else:
    db_path = DATABASE_URL.replace('sqlite:///', '')
    if not db_path or db_path == '.':
        db_path = str(BASE_DIR / 'playstudy_dev.db')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path,
        }
    }

# ─── Custom User Model ───────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

# ─── Password Validation ─────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── REST Framework ──────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '120/minute',
    },
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'DEFAULT_PAGINATION_CLASS': None,
}

# ─── Simple JWT ──────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('REFRESH_TOKEN_EXPIRE_DAYS', '7'))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'sub',
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ─── CORS ─────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'ALLOWED_ORIGINS',
        'http://localhost:8080,http://localhost:5173,http://localhost:3000,http://localhost:8081'
    ).split(',')
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept', 'authorization', 'content-type', 'origin',
    'x-csrftoken', 'x-requested-with',
]
CORS_EXPOSE_HEADERS = [
    'X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset',
]

# ─── Security Headers ────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ─── Redis / Cache ────────────────────────────────────────
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ─── AI Providers ─────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# ─── Static Files ─────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ─── Internationalization ─────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Logging ──────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {name} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ─── File Upload Limits ───────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024
