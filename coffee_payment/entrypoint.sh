#!/bin/sh

# Создаем директорию для логов, если она не существует
mkdir -p /app/logs

# Применяем миграции
python manage.py migrate

# Создаем суперпользователя, если он не существует
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser --no-input || true
fi

# Проверяем режим запуска
if [ "$RUN_MODE" = "development" ]; then
    echo "Starting in development mode..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting in production mode with Gunicorn..."
    exec gunicorn -c gunicorn.conf.py coffee_payment.asgi:application
fi