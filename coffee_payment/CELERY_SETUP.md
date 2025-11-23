# Celery Setup - Background Payment Check

## Обзор

Система фоновой проверки платежей использует Celery для периодической проверки статуса pending заказов.

## Архитектура

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Django    │────▶│    Redis    │◀────│Celery Worker │
│     Web     │     │   (Broker)  │     │              │
└─────────────┘     └─────────────┘     └──────────────┘
                           ▲
                           │
                    ┌──────────────┐
                    │ Celery Beat  │
                    │ (Scheduler)  │
                    └──────────────┘
```

## Компоненты

### 1. Redis
- **Роль**: Брокер сообщений для Celery
- **Порт**: 6379
- **Данные**: Персистентное хранилище (appendonly mode)

### 2. Celery Worker
- **Роль**: Обрабатывает задачи из очереди
- **Задачи**: `check_pending_payments`
- **Логирование**: INFO level

### 3. Celery Beat
- **Роль**: Планировщик периодических задач
- **Расписание**: Каждые 10 секунд запускает `check_pending_payments`

## Запуск с Docker Compose

### Запустить все сервисы:
```bash
docker-compose up -d
```

### Запустить только определенные сервисы:
```bash
# Только Redis
docker-compose up -d redis

# Django + Redis + Celery
docker-compose up -d web celery_worker celery_beat
```

### Просмотр логов:
```bash
# Все сервисы
docker-compose logs -f

# Только Celery Worker
docker-compose logs -f celery_worker

# Только Celery Beat
docker-compose logs -f celery_beat
```

### Остановить сервисы:
```bash
docker-compose down
```

## Локальный запуск (без Docker)

### 1. Установить зависимости:
```bash
pip install -r requirements.txt
```

### 2. Запустить Redis:
```bash
redis-server
```

### 3. Запустить Django:
```bash
python manage.py runserver
```

### 4. Запустить Celery Worker:
```bash
celery -A coffee_payment worker --loglevel=info
```

### 5. Запустить Celery Beat:
```bash
celery -A coffee_payment beat --loglevel=info
```

**Или запустить Worker и Beat вместе:**
```bash
celery -A coffee_payment worker --beat --loglevel=info
```

## Конфигурация

### Настройки в `settings.py`:

```python
# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Background Payment Check
PAYMENT_CHECK_INTERVAL_S = 10          # Интервал запуска задачи
FAST_TRACK_LIMIT_S = 300               # 5 минут для fast track
FAST_TRACK_INTERVAL_S = 5              # Проверка каждые 5 сек (fast)
SLOW_TRACK_INTERVAL_S = 60             # Проверка каждые 60 сек (slow)
PAYMENT_ATTEMPTS_LIMIT = 10            # Максимум попыток
PAYMENT_API_TIMEOUT_S = 3              # Таймаут API запросов
```

### Переменные окружения:

```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Мониторинг

### Проверить статус Celery:
```bash
celery -A coffee_payment inspect active
```

### Проверить зарегистрированные задачи:
```bash
celery -A coffee_payment inspect registered
```

### Проверить расписание Beat:
```bash
celery -A coffee_payment inspect scheduled
```

### Статистика Worker:
```bash
celery -A coffee_payment inspect stats
```

## Логирование

Логи Celery записываются в:
- **Console**: stdout/stderr
- **Django logs**: `logs/coffee_payment.log`

Логгеры:
- `check_pending_payments` - фоновая задача проверки
- `payment_status_service` - сервис обработки статусов

## Troubleshooting

### Celery не подключается к Redis:
```bash
# Проверить, что Redis запущен
redis-cli ping
# Должен вернуть: PONG

# Проверить подключение
redis-cli -h localhost -p 6379
```

### Задачи не выполняются:
```bash
# Проверить, что Worker запущен
celery -A coffee_payment inspect active

# Проверить очередь
celery -A coffee_payment inspect reserved
```

### Beat не запускает задачи:
```bash
# Проверить расписание
celery -A coffee_payment inspect scheduled

# Удалить старый schedule файл
rm celerybeat-schedule
```

## Production рекомендации

### 1. Supervisor (для Linux)
Создать конфигурацию в `/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery_worker]
command=celery -A coffee_payment worker --loglevel=info
directory=/path/to/coffee_payment
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery_beat]
command=celery -A coffee_payment beat --loglevel=info
directory=/path/to/coffee_payment
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

### 2. Systemd (для Linux)
Создать файлы сервисов:

**`/etc/systemd/system/celery-worker.service`:**
```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/coffee_payment
ExecStart=/path/to/venv/bin/celery -A coffee_payment worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/celery-beat.service`:**
```ini
[Unit]
Description=Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/coffee_payment
ExecStart=/path/to/venv/bin/celery -A coffee_payment beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

### 3. Мониторинг
Рекомендуется использовать:
- **Flower** - веб-интерфейс для мониторинга Celery
- **Prometheus + Grafana** - метрики и дашборды
- **Sentry** - отслеживание ошибок

Установка Flower:
```bash
pip install flower
celery -A coffee_payment flower
```

Доступ: http://localhost:5555

## Тестирование

### Запустить тесты:
```bash
pytest tests/test_background_payment_integration.py -v
```

### Ручной запуск задачи:
```python
from payments.tasks import check_pending_payments
check_pending_payments.delay()
```

## Дополнительная информация

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Documentation](https://redis.io/documentation)
- [Django Celery Integration](https://docs.celeryproject.org/en/stable/django/)
