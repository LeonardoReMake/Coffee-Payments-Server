"""
Gunicorn configuration file for Coffee Payments Server.

This configuration supports production deployment with Uvicorn workers for ASGI support.
All parameters are configurable through environment variables with sensible defaults.
"""

import os

# Server socket
bind = f"0.0.0.0:{os.getenv('GUNICORN_PORT', '8000')}"

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', '4'))
worker_class = 'uvicorn.workers.UvicornWorker'

# Timeouts
timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))
graceful_timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))

# Worker lifecycle
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '0'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '0'))

# Logging
# Use Django logging configuration for consistent JSON format
loglevel = os.getenv('LOG_LEVEL', 'INFO').lower()

# Configure loggers to use Django's logging
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "tag": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'handlers': ['console'],
    },
    'loggers': {
        'gunicorn.access': {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'handlers': ['console'],
            'propagate': False,
        },
        'gunicorn.error': {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# Application
wsgi_app = 'coffee_payment.asgi:application'
