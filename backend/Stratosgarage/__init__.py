# Stratosgarage/__init__.py
# Load Celery app at Django startup so @shared_task decorators register correctly.
# Guarded import: Celery is optional during local dev if not installed.
try:
    from .celery import app as celery_app  # noqa: F401
    __all__ = ('celery_app',)
except ImportError:
    pass  # Celery not installed — tasks disabled; install via requirements.txt
