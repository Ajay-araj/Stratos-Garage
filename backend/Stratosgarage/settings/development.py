from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Disable secure cookies for local dev
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Local memory cache or Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
