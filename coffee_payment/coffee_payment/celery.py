"""
Celery configuration for coffee_payment project.
"""

import os
from celery import Celery
from celery.signals import setup_logging

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffee_payment.settings')

app = Celery('coffee_payment')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """
    Configure Celery to use Django logging configuration.
    This ensures all Celery logs use JSON format and output to stdout/stderr.
    """
    from logging.config import dictConfig
    from django.conf import settings
    
    dictConfig(settings.LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
