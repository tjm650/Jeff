import os
from pathlib import Path
from dotenv import load_dotenv
import environ

if not os.getenv('RENDER'):
    load_dotenv()
env = environ.Env()
if not os.getenv('RENDER'):
    environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-development-only')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [x.strip() for x in os.getenv('ALLOWED_HOSTS', '*.onrender.com').split(',') if x.strip()]
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

CORS_ALLOWED_ORIGINS = [x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS', 'https://jeff-one.vercel.app,https://jeff-backend-n5kb.onrender.com').split(',') if x.strip()]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ['DELETE','GET','OPTIONS','PATCH','POST','PUT']
CORS_ALLOW_HEADERS = ['accept','accept-encoding','authorization','content-type','dnt','origin','user-agent','x-csrftoken','x-requested-with','x-api-key']

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication','rest_framework.authentication.BasicAuthentication','core.authentication.APIKeyAuthentication'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','corsheaders','rest_framework','core','matching','providers','whatsapp']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','corsheaders.middleware.CorsMiddleware','core.middleware.SecurityMiddleware','core.middleware.InputValidationMiddleware','core.middleware.LoggingMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'backend.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR / 'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'backend.wsgi.application'
ASGI_APPLICATION = 'backend.asgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': env.db('DATABASE_URL')}
else:
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR / 'db.sqlite3'}}

CACHES = {'default': {'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
CHANNEL_LAYERS = {'default': {'BACKEND':'channels.layers.InMemoryChannelLayer'}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Harare'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
APPEND_SLASH = False
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv('CSRF_TRUSTED_ORIGINS','https://jeff-backend-n5kb.onrender.com').split(',') if x.strip()]
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
DATA_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024 * 1024
JEFF_SETTINGS = {
    'MAX_PROPERTY_RESULTS': int(os.getenv('MAX_PROPERTY_RESULTS','5')),
    'ADMIN_PHONE': os.getenv('ADMIN_PHONE'),
    'WEBHOOK_SECRET': os.getenv('WEBHOOK_SECRET'),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
    'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID'),
    'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN'),
    'TWILIO_WHATSAPP_NUMBER': os.getenv('TWILIO_WHATSAPP_NUMBER'),
    'META_ACCESS_TOKEN': os.getenv('META_ACCESS_TOKEN'),
    'META_PHONE_NUMBER_ID': os.getenv('META_PHONE_NUMBER_ID'),
    'META_APP_SECRET': os.getenv('META_APP_SECRET'),
    'META_VERIFY_TOKEN': os.getenv('META_VERIFY_TOKEN'),
    'META_API_VERSION': os.getenv('META_API_VERSION','v20.0'),
    'META_WHATSAPP_NUMBER': os.getenv('META_WHATSAPP_NUMBER'),
    'MAX_UPLOAD_SIZE': 16 * 1024 * 1024,
    'UPLOAD_PATH': 'uploads',
    'PRIVACY_POLICY_URL': f"{os.getenv('NEXT_PUBLIC_FRONTEND_URL','')}/privacy",
}
AI_ALLOWED_MODELS = ['core.Property']
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'INFO'}}
os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https')
    USE_X_FORWARDED_HOST = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
