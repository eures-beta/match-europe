import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME = BASE_DIR / '.runtime'
RUNTIME.mkdir(exist_ok=True)
DEMO_MODE = os.environ.get('ME_DEMO_MODE', '1') == '1'
DEBUG = os.environ.get('ME_DEBUG', '0') == '1'
SECRET_KEY = os.environ.get('ME_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEMO_MODE:
        raise RuntimeError('ME_SECRET_KEY is required outside demonstration mode')
    secret_path = RUNTIME / 'secret'
    if not secret_path.exists():
        with secret_path.open('x') as output:
            output.write(secrets.token_urlsafe(64))
        secret_path.chmod(0o600)
    SECRET_KEY = secret_path.read_text().strip()
ALLOWED_HOSTS = os.environ.get('ME_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1],testserver').split(',')
CSRF_TRUSTED_ORIGINS = [x for x in os.environ.get('ME_CSRF_TRUSTED_ORIGINS', '').split(',') if x]
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
                  'django.contrib.messages', 'django.contrib.staticfiles', 'journeys']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.locale.LocaleMiddleware', 'django.middleware.common.CommonMiddleware',
              'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',
              'journeys.views.interface']}}]
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ.get('PGDATABASE', 'me_local'),
                        'USER': os.environ.get('PGUSER', os.environ.get('USER', 'postgres')),
                        'PASSWORD': os.environ.get('PGPASSWORD', ''), 'HOST': os.environ.get('PGHOST', str(RUNTIME / 'pgsocket')),
                        'PORT': os.environ.get('PGPORT', '55432')}}
LANGUAGE_CODE = 'fr'
LANGUAGES = [('fr', 'Français'), ('en', 'English'), ('de', 'Deutsch')]
LOCALE_PATHS = [BASE_DIR / 'locale']
USE_I18N = True
USE_TZ = True
TIME_ZONE = 'Europe/Paris'
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = RUNTIME / 'static'
MEDIA_ROOT = RUNTIME / 'private'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_COOKIE_SECURE = os.environ.get('ME_HTTPS', '0') == '1'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
LOGIN_URL = '/access/'
LOGGING = {'version': 1, 'disable_existing_loggers': False,
           'filters': {'redact_links': {'()': 'config.logging.RedactAccessLinks'}},
           'handlers': {'safe_console': {'class': 'logging.StreamHandler', 'filters': ['redact_links']}},
           'loggers': {'django.server': {'handlers': ['safe_console'], 'level': 'INFO', 'propagate': False},
                       'django.request': {'handlers': ['safe_console'], 'level': 'WARNING', 'propagate': False}}}
if not DEMO_MODE:
    raise RuntimeError('Live mode is intentionally unavailable until external adapters and operational controls are verified.')
