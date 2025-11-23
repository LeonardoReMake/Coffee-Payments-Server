# Исправление проблемы со статическими файлами в продакшене

## Проблема
Django admin не загружал статические файлы (JS, CSS) в production режиме, что приводило к ошибкам 404.

## Решение
Добавлен WhiteNoise для раздачи статических файлов через Gunicorn.

## Что изменено

1. **requirements.txt** - добавлен `whitenoise>=6.6.0`
2. **settings.py**:
   - Добавлен `STATIC_ROOT = BASE_DIR / 'staticfiles'`
   - Настроен `STORAGES` с `CompressedManifestStaticFilesStorage`
   - Добавлен `WhiteNoiseMiddleware` в MIDDLEWARE (сразу после SecurityMiddleware)
3. **entrypoint.sh** - добавлен `collectstatic --noinput` перед запуском Gunicorn
4. **.gitignore** - добавлена директория `staticfiles/`

## Деплой обновления

```bash
# 1. Пересобрать образ Docker
docker-compose build web

# 2. Перезапустить контейнеры
docker-compose down
docker-compose up -d

# Статика соберется автоматически при запуске
```

## Проверка
После перезапуска админка Django должна корректно загружать все статические файлы (JS, CSS).
