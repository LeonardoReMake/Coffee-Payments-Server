#!/bin/sh

# Применяем миграции
python manage.py makemigrations
python manage.py migrate

# Создаем суперпользователя, если он не существует
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser --no-input || true
fi

# Запускаем сервер
exec "$@"