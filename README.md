# Coffee-Payments-Server
Server for payments app for coffee machines

## Environment Variables

This table documents all environment variables that can be configured in the application.

| Variable Name | Description | Default Value |
|--------------|-------------|---------------|
| **Django Core** | | |
| `SECRET_KEY` | Django secret key for cryptographic signing | `django-insecure-)8hc120s$c)^11n^fl==uogtt9e(qlu^(vc8u%hfy_67to6ox%` |
| `DEBUG` | Enable/disable debug mode | `True` |
| `ALLOWED_HOSTS` | List of allowed host/domain names | `localhost, 127.0.0.1, pay.tmetr.ru` |
| `BASE_URL` | Base URL for the application | `pay.tmetr.ru` |
| `CSRF_TRUSTED_ORIGINS` | List of trusted origins for CSRF | `https://pay.tmetr.ru` |
| `DJANGO_SUPERUSER_USERNAME` | Username for Django superuser (used in automated setup) | — |
| `DJANGO_SUPERUSER_PASSWORD` | Password for Django superuser (used in automated setup) | — |
| `DJANGO_SUPERUSER_EMAIL` | Email for Django superuser (used in automated setup) | — |
| **Database Configuration** | | |
| `DB_NAME` | PostgreSQL database name | — |
| `DB_USER` | PostgreSQL database user | — |
| `DB_PASSWORD` | PostgreSQL database password | — |
| `DB_HOST` | PostgreSQL database host | — |
| `DB_PORT` | PostgreSQL database port | — |
| **PostgreSQL SSL** | | |
| `POSTGRES_SSL_MODE` | SSL mode (disable, allow, prefer, require, verify-ca, verify-full) | — |
| `POSTGRES_SSL_CERT` | Path to client certificate file | — |
| `POSTGRES_SSL_KEY` | Path to client key file | — |
| `POSTGRES_SSL_ROOT_CERT` | Path to root certificate file | — |
| **TMetr API** | | |
| `TMETR_TOKEN` | JWT token for Tmetr API authentication | (default test token provided) |
| `TMETR_HOST` | Tmetr API host | `test.telemetry.fwsoft.ru` |
| **Celery** | | |
| `CELERY_BROKER_URL` | Redis URL for Celery broker | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery result backend | `redis://localhost:6379/0` |
| `SKIP_MIGRATIONS` | Skip database migrations on startup (for Celery workers) | — |
| **Application Settings** | | |
| `ORDER_EXPIRATION_MINUTES` | Time in minutes before an order expires | `15` |
| `DEVICE_ONLINE_THRESHOLD_MINUTES` | Time threshold for device online status | `15` |
| `PAYMENT_SCENARIOS` | Available payment scenarios | `['Yookassa', 'YookassaReceipt', 'TBank', 'Custom']` |
| `DEFAULT_PAYMENT_SCENARIO` | Default payment scenario for new devices | `Yookassa` |
| **Background Payment Check** | | |
| `PAYMENT_CHECK_INTERVAL_S` | Interval for running background payment check task (seconds) | `5` |
| `FAST_TRACK_LIMIT_S` | Time threshold for fast vs slow track (seconds) | `300` |
| `FAST_TRACK_INTERVAL_S` | Check interval for fast track payments (seconds) | `2` |
| `SLOW_TRACK_INTERVAL_S` | Check interval for slow track payments (seconds) | `60` |
| `PAYMENT_ATTEMPTS_LIMIT` | Maximum check attempts before marking as failed | `50` |
| `PAYMENT_API_TIMEOUT_S` | Timeout for payment provider API calls (seconds) | `3` |
| **TBank API** | | |
| `SHOP_ID` | TBank shop ID | `<ShopID>` |
| `T_BANK_BASE_URL` | TBank API base URL | `https://securepay.tinkoff.ru` |
| **Logging** | | |
| `LOGGING` | Django logging configuration | (configured in settings.py) |
| **Gunicorn Production Server** | | |
| `GUNICORN_WORKERS` | Number of Gunicorn worker processes | `4` |
| `GUNICORN_PORT` | Port for Gunicorn to bind to | `8000` |
| `GUNICORN_TIMEOUT` | Request timeout in seconds | `30` |
| `GUNICORN_MAX_REQUESTS` | Requests before worker restart (0 = unlimited) | `0` |
| `GUNICORN_MAX_REQUESTS_JITTER` | Random jitter for worker restart | `0` |
| `RUN_MODE` | Server mode: `development` or `production` | `production` |

**Note:** Variables marked with "—" have no default value and must be provided in production environments. Sensitive values (SECRET_KEY, API keys, database credentials) should be stored securely and not committed to version control.
