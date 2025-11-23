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
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'

# Application
wsgi_app = 'coffee_payment.asgi:application'
