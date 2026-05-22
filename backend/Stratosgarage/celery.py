"""
Celery application for Stratos Garage.
Import in Stratosgarage/__init__.py so Celery auto-discovers tasks.
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.development')

app = Celery('Stratosgarage')

# Read config from Django settings, namespace CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
