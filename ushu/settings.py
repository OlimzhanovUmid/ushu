"""
Django settings for ushu project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Configuration comes from the environment (the launcher writes an env file
# next to it); the defaults below are for local development only.

def _env_bool(name, default):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


# SECURITY WARNING: production supplies USHU_SECRET_KEY; the historical
# committed key must not be used to sign anything real.
SECRET_KEY = os.environ.get(
    'USHU_SECRET_KEY',
    'dev-insecure-do-not-use-in-production-set-USHU_SECRET_KEY',
)

# SECURITY WARNING: production launcher sets USHU_DEBUG=0.
DEBUG = _env_bool('USHU_DEBUG', True)

# Comma-separated hosts; '*' suits an isolated venue LAN reached by IP.
ALLOWED_HOSTS = [h.strip() for h in
                 os.environ.get('USHU_ALLOWED_HOSTS', '*').split(',') if h.strip()]

# Audience-facing monitor branding (was hardcoded in the template).
EVENT_TITLE = os.environ.get('USHU_EVENT_TITLE', "O'ZBEKISTON USHU FEDERATSIYASI")
EVENT_SUBTITLE = os.environ.get('USHU_EVENT_SUBTITLE', "O'RTA OSIYO CHEMPIONATI")

# The venue runs on an isolated plain-HTTP LAN with no TLS, so the *_COOKIE_SECURE
# flags are intentionally left unset — enabling them would stop cookies from being
# sent over HTTP and break every client. `manage.py check --deploy` will warn
# about this (security.W012/W016); the warning is accepted for this trust model.

# Keep the historical 32-bit AutoField primary keys (the existing DB schema
# uses them); avoids a needless BigAutoField migration on Django >= 3.2.
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'sortedm2m',

    'core',

    'judges',  # no dependency
    'clubs',  # no dependency
    'elements',  # no dependency
    'participants',  # 'elements', 'clubs'
    'tablo',  # 'core', 'judges', 'elements', 'participants'
)

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves static files with DEBUG off; keep it near the top.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
)

ROOT_URLCONF = 'ushu.urls'

WSGI_APPLICATION = 'ushu.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        # Busy-timeout for ~10 concurrent judge writers. WAL journal mode and
        # busy_timeout PRAGMA are also applied per-connection in core.apps.
        'OPTIONS': {
            'timeout': 20,
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'ru-RU'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# WhiteNoise: gzip static assets, no hashed manifest (the collected tree is
# not manifest-clean and manifest storage would 500 on any missing reference).
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}
# Serve media (country flags) through Django on the LAN even with DEBUG off.
SERVE_MEDIA = _env_bool('USHU_SERVE_MEDIA', True)

LOGIN_URL = '/login'
LOGOUT_URL = '/logout'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
AUTH_USER_MODEL = 'judges.User'

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Оставляем пустым — шаблоны в приложениях
        'APP_DIRS': True,  # Включает автоматический поиск templates в приложениях
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'core.context_processors.event_branding',
            ],
        },
    },
]

# TEMPLATE_CONTEXT_PROCESSORS = (
#     'django.contrib.auth.context_processors.auth',
#     'django.template.context_processors.debug',
#     'django.template.context_processors.i18n',
#     'django.template.context_processors.media',
#     'django.template.context_processors.static',
#     'django.template.context_processors.tz',
#     'django.template.context_processors.request',
#     'django.contrib.messages.context_processors.messages',
# )

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
