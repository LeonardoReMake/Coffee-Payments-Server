# Production Deployment Guide

## Quick Start

### 1. Подготовка переменных окружения

Скопируйте пример файла и заполните реальными значениями:

```bash
cp .env.production.example .env.production
nano .env.production  # или используйте любой редактор
```

**Важно:** Убедитесь, что установлены следующие переменные:
- `GUNICORN_PORT=8080` (должен совпадать с портом в nginx)
- `RUN_MODE` НЕ должен быть установлен в `development` (или вообще не установлен)
- `DEBUG=False`
- `SECRET_KEY` - уникальный секретный ключ
- Корректные данные для подключения к БД

### 2. Запуск на production сервере

```bash
# Остановить старые контейнеры
docker-compose down

# Пересобрать образы
docker-compose build

# Запустить с production переменными
docker-compose --env-file .env.production up -d
```

### 3. Проверка статуса

```bash
# Проверить логи web контейнера
docker-compose logs -f web

# Проверить, что Gunicorn запустился
docker-compose logs web | grep "Gunicorn"

# Проверить, что приложение слушает на порту 8080
docker-compose exec web netstat -tlnp | grep 8080
```

### 4. Проверка работоспособности

```bash
# Проверить health check
curl http://localhost:8080/health

# Должен вернуть:
# {"status": "healthy", "timestamp": "..."}
```

## Troubleshooting

### Ошибка 502 Bad Gateway

**Причина:** Nginx не может подключиться к приложению.

**Решение:**
1. Проверьте, что `GUNICORN_PORT=8080` установлен
2. Проверьте логи: `docker-compose logs web`
3. Убедитесь, что Gunicorn запустился: `docker-compose logs web | grep "Starting in production mode"`
4. Проверьте, что порт 8080 слушается: `docker-compose exec web netstat -tlnp | grep 8080`

### Приложение не запускается

**Причина:** Ошибка в конфигурации или зависимостях.

**Решение:**
1. Проверьте логи: `docker-compose logs web`
2. Убедитесь, что все зависимости установлены: `docker-compose exec web pip list | grep gunicorn`
3. Проверьте переменные окружения: `docker-compose exec web env | grep GUNICORN`

### База данных недоступна

**Причина:** Проблемы с подключением к PostgreSQL.

**Решение:**
1. Проверьте, что контейнер БД запущен: `docker-compose ps db`
2. Проверьте переменные подключения: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
3. Проверьте логи БД: `docker-compose logs db`

## Конфигурация логирования

Приложение выводит все логи в stdout/stderr в JSON формате.

**Переменная окружения:**
- `LOG_LEVEL` - Управляет детализацией логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- По умолчанию: INFO

**Конфигурация Kubernetes:**
- Логи автоматически собираются Kubernetes
- Настройте систему лог-агрегации (Loki, ELK, CloudWatch) для парсинга JSON логов
- Установите политики хранения логов в системе лог-агрегации

**Мониторинг:**
- Используйте систему лог-агрегации для поиска и анализа логов
- Настройте алерты на основе уровней ERROR и CRITICAL
- Мониторьте объем и производительность логов

**Пример установки LOG_LEVEL:**
```bash
# В .env.production
LOG_LEVEL=INFO

# Для отладки
LOG_LEVEL=DEBUG
```

## Мониторинг

### Логи приложения

```bash
# Все логи (в JSON формате)
docker-compose logs -f

# Только web
docker-compose logs -f web

# Только Celery
docker-compose logs -f celery_worker celery_beat
```

**Формат логов:**
Все логи выводятся в JSON формате для удобного парсинга:
```json
{"timestamp": "2025-11-24T10:30:00+00:00", "tag": "django.request", "level": "INFO", "message": "GET /v1/pay HTTP/1.1 200"}
```

### Метрики Gunicorn

Gunicorn логирует:
- Количество workers
- Запросы (access log в stdout)
- Ошибки (error log в stderr)
- Worker restarts

### Health Check

Endpoint: `GET /health`

Используется Kubernetes для readiness и liveness проб.

## Обновление приложения

```bash
# 1. Получить новый код
git pull

# 2. Пересобрать образы
docker-compose build

# 3. Перезапустить контейнеры (graceful restart)
docker-compose up -d

# 4. Проверить логи
docker-compose logs -f web
```

## Откат к предыдущей версии

```bash
# 1. Вернуться к предыдущему коммиту
git checkout <previous-commit>

# 2. Пересобрать и перезапустить
docker-compose build
docker-compose up -d
```

## Полезные команды

```bash
# Проверить статус всех контейнеров
docker-compose ps

# Перезапустить только web
docker-compose restart web

# Выполнить команду в контейнере
docker-compose exec web python manage.py <command>

# Подключиться к контейнеру
docker-compose exec web /bin/sh

# Проверить использование ресурсов
docker stats
```
