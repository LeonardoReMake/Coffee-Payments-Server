# Design Document

## Overview

Данный документ описывает проектное решение для рефакторинга логики обработки QR-кодов в системе Coffee Payments Server. Цель рефакторинга — устранить несоответствие между функциями `qr_code_redirect` и `yookassa_payment_process`, объединив их логику в единый поток обработки платежей с автоматическим определением платежного сценария.

## Architecture

### Current Architecture (Проблема)

```
Пользователь сканирует QR-код
        ↓
GET /v1/pay?deviceUuid=...&drinkNo=...&size=...
        ↓
qr_code_redirect()
        ↓
validate_device() + validate_merchant()
        ↓
get_redirect_url() → Device.redirect_url
        ↓
HttpResponseRedirect(Device.redirect_url + query_params)
        ↓
[Внешний редирект - логика сценария теряется]
```

**Проблемы:**
1. Логика определения платежного сценария не используется
2. Промежуточный редирект на `Device.redirect_url` не нужен для Yookassa/TBank
3. Функция `yookassa_payment_process` имеет неправильное название
4. Дублирование логики валидации

### Target Architecture (Решение)

```
Пользователь сканирует QR-код
        ↓
GET /v1/pay?deviceUuid=...&drinkNo=...&size=...&uuid=...
        ↓
process_payment_flow() [переименованная yookassa_payment_process]
        ↓
Валидация параметров + Device + Merchant
        ↓
Получение информации о напитке (Tmetr API)
        ↓
Создание Order (status='created')
        ↓
Определение Payment Scenario (device.payment_scenario)
        ↓
    ┌─────────────────────────────────────┐
    │                                     │
    ▼                                     ▼
Yookassa/TBank                      Custom
    │                                     │
    ▼                                     ▼
show_order_info()              execute_custom_scenario()
    │                                     │
    ▼                                     │
initiate_payment()                       │
    │                                     │
    ▼                                     ▼
PaymentScenarioService.execute_scenario()
    │
    ▼
HttpResponseRedirect(payment_url)
```

## Components and Interfaces

### 1. View Functions

#### 1.1 `process_payment_flow()` (переименованная `yookassa_payment_process`)

**Назначение:** Основная функция обработки платежного потока после сканирования QR-кода.

**Входные параметры (GET):**
- `deviceUuid` (required) — UUID кофемашины
- `drinkNo` (required) — ID напитка на устройстве
- `drinkName` (required) — название напитка
- `size` (required) — размер напитка (0=маленький, 1=средний, 2=большой)
- `uuid` (required) — UUID заказа

**Логика:**
1. Валидация всех обязательных параметров
2. Получение Device по `deviceUuid`
3. Валидация Merchant (проверка `valid_until`)
4. Получение информации о напитке через `TmetrService.send_static_drink()`
5. Создание Order со статусом `'created'`
6. Определение `device.payment_scenario`
7. Маршрутизация:
   - Если `Yookassa` или `TBank` → `show_order_info()`
   - Если `Custom` → `PaymentScenarioService.execute_scenario()`

**Возвращаемые значения:**
- `HttpResponse` — HTML страница с информацией о заказе (для Yookassa/TBank)
- `HttpResponseRedirect` — редирект на платежную страницу (для Custom)
- `HttpResponse` — страница ошибки (при ошибках)

**Обработка ошибок:**
- Отсутствие параметров → 400 (Bad Request)
- Device не найдено → 404 (Not Found)
- Merchant истек → 403 (Forbidden)
- Ошибка Tmetr API → 503 (Service Unavailable)
- Отсутствие credentials → 503 (Service Unavailable)

#### 1.2 `qr_code_redirect()` (устаревшая, будет удалена)

**Статус:** Функция будет удалена, так как её логика интегрирована в `process_payment_flow()`.

**Миграционный план:**
- URL `/v1/pay` будет перенаправлен на `process_payment_flow`
- URL `/v1/tbank-pay` будет перенаправлен на `process_payment_flow`
- Старый URL `/v1/yook-pay` останется как алиас для обратной совместимости

### 2. Service Layer

#### 2.1 `qr_code_service.py` (рефакторинг)

**Изменения:**
- Функция `get_redirect_url()` будет удалена (больше не нужна)
- Функции `validate_device()` и `validate_merchant()` останутся для переиспользования

**Новая структура:**

```python
def validate_device(device_uuid):
    """
    Validates device existence by device_uuid.
    
    Args:
        device_uuid: UUID of the device
        
    Returns:
        Device: Device instance
        
    Raises:
        Http404: If device not found
    """
    device = get_object_or_404(Device, device_uuid=device_uuid)
    return device

def validate_merchant(device):
    """
    Validates merchant permissions for the device.
    
    Args:
        device: Device instance
        
    Returns:
        Merchant: Merchant instance
        
    Raises:
        ValueError: If merchant permissions expired
        Http404: If merchant not found
    """
    merchant = get_object_or_404(Merchant, id=device.merchant_id)
    if hasattr(merchant, 'valid_until') and merchant.valid_until <= datetime.now().date():
        raise ValueError("Merchant permissions expired")
    return merchant
```

#### 2.2 `payment_scenario_service.py` (без изменений)

Сервис остается без изменений, так как он уже корректно обрабатывает все сценарии.

### 3. URL Configuration

**Новая конфигурация (`coffee_payment/urls.py`):**

```python
from payments.views import (
    process_payment_flow,  # Новое имя
    process_payment,
    yookassa_payment_result_webhook,
    initiate_payment
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Main payment flow endpoint (новый основной эндпоинт)
    path('v1/pay', process_payment_flow, name='process_payment_flow'),
    
    # Legacy aliases for backward compatibility
    path('v1/tbank-pay', process_payment_flow, name='tbank_pay_legacy'),
    path('v1/yook-pay', process_payment_flow, name='yook_pay_legacy'),
    
    # Payment processing endpoints
    path('v1/process_payment/', process_payment, name='process_payment'),
    path('v1/initiate-payment', initiate_payment, name='initiate_payment'),
    
    # Webhook endpoints
    path('v1/yook-pay-webhook', yookassa_payment_result_webhook, name='yookassa_payment_result_webhook'),
]
```

## Data Models

Изменений в моделях данных не требуется. Используются существующие модели:

- `Device` — с полями `device_uuid`, `payment_scenario`, `redirect_url`, `logo_url`, `client_info`
- `Order` — с полями `status`, `expires_at`, `external_order_id`, `drink_name`, `size`, `price`
- `Merchant` — с полем `valid_until`
- `MerchantCredentials` — для хранения учетных данных платежных систем

## Error Handling

### Централизованные сообщения об ошибках

Все пользовательские сообщения об ошибках хранятся в `payments/user_messages.py`:

```python
ERROR_MESSAGES = {
    'missing_parameters': 'Отсутствуют обязательные параметры запроса',
    'device_not_found': 'Устройство не найдено',
    'merchant_expired': 'Доступ к устройству запрещен',
    'service_unavailable': 'Сервис временно недоступен',
    'missing_credentials': 'Платежная система не настроена для данного устройства',
    'order_not_found': 'Заказ не найден',
    'order_expired': 'Время заказа истекло',
    'invalid_request': 'Некорректный запрос',
    'payment_creation_failed': 'Не удалось создать платеж',
}
```

### Обработка ошибок по слоям

#### View Layer (`process_payment_flow`)

```python
try:
    # Валидация параметров
    if not all([device_uuid, drink_name, drink_number, order_uuid, drink_size]):
        log_error('Missing required parameters', 'process_payment_flow', 'ERROR')
        return render_error_page(ERROR_MESSAGES['missing_parameters'], 400)
    
    # Валидация Device и Merchant
    device = validate_device(device_uuid)
    validate_merchant(device)
    
    # Получение информации о напитке
    drink_details = tmetr_service.send_static_drink(...)
    
    # Создание Order
    order = Order.objects.create(...)
    
    # Маршрутизация по сценарию
    if device.payment_scenario in ['Yookassa', 'TBank']:
        return show_order_info(request, device, order, drink_details)
    else:
        return PaymentScenarioService.execute_scenario(device, order, drink_details)
        
except Http404:
    log_error(f'Device not found: {device_uuid}', 'process_payment_flow', 'ERROR')
    return render_error_page(ERROR_MESSAGES['device_not_found'], 404)
    
except ValueError as e:
    log_error(f'Merchant validation failed: {str(e)}', 'process_payment_flow', 'FORBIDDEN')
    return render_error_page(ERROR_MESSAGES['merchant_expired'], 403)
    
except requests.RequestException as e:
    log_error(f'Tmetr API request failed: {str(e)}', 'process_payment_flow', 'ERROR')
    return render_error_page(ERROR_MESSAGES['service_unavailable'], 503)
    
except Exception as e:
    log_error(f'Unexpected error: {str(e)}', 'process_payment_flow', 'ERROR')
    return render_error_page(ERROR_MESSAGES['service_unavailable'], 500)
```

#### Service Layer (`PaymentScenarioService`)

Сервисный слой пробрасывает исключения наверх:
- `ValueError` — для ошибок конфигурации (отсутствие credentials, redirect_url)
- `Exception` — для других ошибок

View layer отлавливает эти исключения и преобразует в понятные пользователю сообщения.

## Testing Strategy

### Unit Tests

#### 1. Тесты для `process_payment_flow()`

**Файл:** `coffee_payment/tests/test_payment_flow.py`

**Тестовые сценарии:**

1. **test_process_payment_flow_yookassa_success**
   - Проверка успешного создания заказа для сценария Yookassa
   - Проверка отображения экрана информации о заказе
   - Проверка статуса Order = 'created'

2. **test_process_payment_flow_tbank_success**
   - Проверка успешного создания заказа для сценария TBank
   - Проверка отображения экрана информации о заказе

3. **test_process_payment_flow_custom_success**
   - Проверка прямого редиректа для сценария Custom
   - Проверка, что экран информации НЕ отображается

4. **test_process_payment_flow_missing_parameters**
   - Проверка обработки отсутствующих параметров
   - Проверка HTTP статуса 400

5. **test_process_payment_flow_device_not_found**
   - Проверка обработки несуществующего Device
   - Проверка HTTP статуса 404

6. **test_process_payment_flow_merchant_expired**
   - Проверка обработки истекшего Merchant
   - Проверка HTTP статуса 403

7. **test_process_payment_flow_tmetr_api_failure**
   - Проверка обработки ошибки Tmetr API
   - Проверка HTTP статуса 503

8. **test_process_payment_flow_missing_credentials**
   - Проверка обработки отсутствующих credentials
   - Проверка HTTP статуса 503

#### 2. Тесты для `qr_code_service.py`

**Файл:** `coffee_payment/tests/test_qr_code_service.py`

**Тестовые сценарии:**

1. **test_validate_device_success**
   - Проверка успешной валидации существующего Device

2. **test_validate_device_not_found**
   - Проверка выброса Http404 для несуществующего Device

3. **test_validate_merchant_success**
   - Проверка успешной валидации активного Merchant

4. **test_validate_merchant_expired**
   - Проверка выброса ValueError для истекшего Merchant

### Integration Tests

**Файл:** `coffee_payment/tests/test_payment_flow_integration.py`

**Тестовые сценарии:**

1. **test_full_payment_flow_yookassa**
   - End-to-end тест: QR-код → создание Order → экран информации → инициация платежа → webhook
   - Проверка всех переходов статусов Order

2. **test_full_payment_flow_custom**
   - End-to-end тест: QR-код → создание Order → редирект на внешний URL
   - Проверка параметров редиректа

### Test Configuration

Все тесты должны:
- Использовать `@timeout_decorator.timeout(30)` для ограничения времени выполнения
- Использовать фикстуры для создания тестовых данных (Device, Merchant, MerchantCredentials)
- Мокировать внешние API (Tmetr, Yookassa, TBank)
- Запускаться из директории `coffee_payment/tests/`

## Logging Strategy

### Логирование в `process_payment_flow()`

```python
# Начало обработки
log_info(
    f"Starting payment flow. Request params: deviceUuid={device_uuid}, "
    f"drinkNo={drink_number}, drinkName={drink_name}, size={drink_size}, uuid={order_uuid}",
    'process_payment_flow'
)

# После валидации Device
log_info(
    f"Device validated: {device.device_uuid}, payment_scenario={device.payment_scenario}",
    'process_payment_flow'
)

# После получения информации о напитке
log_info(
    f"Drink details retrieved: price={drink_price}, name={drink_name}",
    'process_payment_flow'
)

# После создания Order
log_info(
    f"Order {order.id} created with status 'created'. "
    f"Payment scenario: {device.payment_scenario}",
    'process_payment_flow'
)

# При маршрутизации
log_info(
    f"Routing to scenario handler: {device.payment_scenario} for Order {order.id}",
    'process_payment_flow'
)

# При ошибках
log_error(
    f"Error details with full context",
    'process_payment_flow',
    'ERROR'
)
```

### Формат логов

Все логи должны содержать:
1. Контекст операции (device_uuid, order_id, scenario)
2. Все параметры запроса (для отладки)
3. Результат операции (успех/ошибка)
4. Временные метки (автоматически добавляются логгером)

## Migration Plan

### Этап 1: Подготовка

1. Создать новую функцию `process_payment_flow()` с объединенной логикой
2. Обновить URL конфигурацию с алиасами для обратной совместимости
3. Обновить все логи с новым именем функции

### Этап 2: Тестирование

1. Запустить все существующие тесты
2. Создать новые тесты для `process_payment_flow()`
3. Провести интеграционное тестирование

### Этап 3: Деплой

1. Задеплоить новую версию с алиасами URL
2. Мониторить логи на наличие ошибок
3. Проверить работу всех сценариев (Yookassa, TBank, Custom)

### Этап 4: Очистка (опционально, в будущем)

1. Удалить функцию `qr_code_redirect()` после подтверждения, что она не используется
2. Удалить функцию `get_redirect_url()` из `qr_code_service.py`
3. Удалить устаревшие URL алиасы (если не требуется обратная совместимость)

## Security Considerations

1. **Валидация параметров:** Все входные параметры должны валидироваться перед использованием
2. **CSRF защита:** Используется `@csrf_exempt` только для webhook эндпоинтов
3. **Логирование:** Не логировать чувствительные данные (секретные ключи, токены)
4. **Таймауты:** Все запросы к внешним API должны иметь таймауты
5. **Обработка ошибок:** Не раскрывать технические детали ошибок пользователю

## Performance Considerations

1. **Кэширование:** Device и Merchant данные могут быть закэшированы (опционально)
2. **Асинхронность:** Запросы к Tmetr API выполняются синхронно (достаточно для MVP)
3. **Индексы БД:** Убедиться, что есть индексы на `device_uuid` и `external_order_id`
4. **Таймауты запросов:** Установить разумные таймауты для внешних API (5-10 секунд)

## Documentation Updates

После реализации необходимо обновить:

1. **PROJECT.md:**
   - Обновить описание потока данных "Инициирование платежа (QR-код)"
   - Обновить раздел "Основные файлы и директории"
   - Добавить информацию о новой функции `process_payment_flow()`

2. **README.md:**
   - Обновить примеры использования API
   - Обновить описание эндпоинтов

3. **Комментарии в коде:**
   - Добавить docstrings для `process_payment_flow()`
   - Обновить комментарии в URL конфигурации
