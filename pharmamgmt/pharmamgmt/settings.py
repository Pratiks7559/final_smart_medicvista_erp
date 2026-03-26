import os
from pathlib import Path

# BASE_DIR points to: pharmamgmt/ (the folder containing manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# SECURITY
# ============================================================
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-5&j%-b#2a$=_!)^-n2x7iq9m$w!%gp-w$(-e8+b3*q$nkol-+k')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost,http://127.0.0.1'
).split(',')

# ============================================================
# APPS & MIDDLEWARE
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.year_filter_middleware.YearFilterMiddleware',
    'core.auth_middleware.LoginRequiredMiddleware',
]

ROOT_URLCONF = 'pharmamgmt.urls'
WSGI_APPLICATION = 'pharmamgmt.wsgi.application'
AUTH_USER_MODEL = 'core.Web_User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# TEMPLATES
# BASE_DIR/templates is the single templates directory
# ============================================================
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
                'core.context_processors.year_context',
            ],
        },
    },
]

# ============================================================
# DATABASE
# Override via environment variables for production
# ============================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'pharma_db'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Pratik@123'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ============================================================
# STATIC FILES
# BASE_DIR/static  → source files (your CSS/JS)
# BASE_DIR/staticfiles → collectstatic output (for production)
# ============================================================
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# ============================================================
# MEDIA FILES
# ============================================================
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# SESSION
# ============================================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = False

# ============================================================
# AUTH
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ============================================================
# INTERNATIONALISATION
# ============================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = False

# ============================================================
# MISC
# ============================================================
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50000
PAGINATION_ITEMS_PER_PAGE = 50

# ============================================================
# CACHE  (use Redis in production via REDIS_URL env var)
# ============================================================
if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
            'KEY_PREFIX': 'pharma',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }

# ============================================================
# LOGGING
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
