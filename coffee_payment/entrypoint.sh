#!/bin/sh

# Применяем миграции только для web сервиса (не для celery workers)
# Это предотвращает race condition при одновременном запуске миграций
if [ "$SKIP_MIGRATIONS" != "true" ]; then
    echo "Running database migrations..."
    python manage.py migrate
    
    # Создаем суперпользователя, если он не существует
    if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
        python manage.py createsuperuser --no-input || true
    fi
else
    echo "Skipping migrations (SKIP_MIGRATIONS=true)"
fi

# Собираем статические файлы для production
if [ "$RUN_MODE" != "development" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

# Проверяем режим запуска
if [ "$RUN_MODE" = "development" ]; then
    # Используем GUNICORN_PORT для единообразия портов
    PORT=${GUNICORN_PORT:-8000}
    echo "Starting in development mode on port $PORT..."
    exec python manage.py runserver 0.0.0.0:$PORT
else
    echo "Starting in production mode with Gunicorn..."
    exec gunicorn -c gunicorn.conf.py coffee_payment.asgi:application
fi