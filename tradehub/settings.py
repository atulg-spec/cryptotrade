import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY
SECRET_KEY = 'django-insecure-zaea+i*&noml4wqe+l1!5=axtm_gxurd*hz8jku&u6qw$x=4jk'
DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '10.10.200.207',
]


# APPS
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'channels',
    'accounts',
    'dashboard',
    'payments',
    'stockmanagement',
    'assets',
]

AUTH_USER_MODEL = 'accounts.CustomUser'


# MIDDLEWARE
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# URL / TEMPLATE
ROOT_URLCONF = 'tradehub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'dashboard.context_processors.site_settings_context',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tradehub.wsgi.application'


# DATABASE
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# I18N
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# STATIC / MEDIA
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# AUTH REDIRECTS
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_URL = 'logout'
LOGOUT_REDIRECT_URL = 'login'


# MISC
DATA_UPLOAD_MAX_NUMBER_FIELDS = 8000
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# CHANNELS
ASGI_APPLICATION = 'tradehub.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


# 🔴 مهم‌ترین بخش برای حل CSRF در موبایل
CSRF_TRUSTED_ORIGINS = [
    "https://eserviceindia.in",
    "https://www.eserviceindia.in",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
    "http://10.10.200.207:8001",
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False