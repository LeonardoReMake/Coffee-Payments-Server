# Design Document

## Overview

Данный дизайн описывает добавление нового статуса заказа `make_failed` в систему обработки платежей кофейных автоматов. Статус используется для обработки ситуаций, когда команда на приготовление напитка не может быть отправлена на кофемашину из-за технических проблем с API Tmetr.

Основная цель — обеспечить корректную обработку ошибок при отправке команды приготовления и предоставить пользователям понятную информацию о проблеме.

## Architecture

### Компоненты системы

Изменения затрагивают следующие компоненты:

1. **Order Model** — добавление нового статуса в список допустимых значений
2. **Device Model** — добавление поля для статус-специфичной информации
3. **Payment Webhook Handler** — обработка ошибок при отправке команды приготовления
4. **Order Status Page** — отображение нового статуса пользователю
5. **User Messages** — добавление описания статуса в централизованное хранилище

### Диаграмма потока данных

```
Платежная система (Yookassa/TBank)
        ↓
    Webhook уведомление
        ↓
yookassa_payment_result_webhook()
        ↓
    Проверка типа события
        ↓
    payment.succeeded?
        ↓ (да)
    Обновление статуса: pending → paid
        ↓
    TmetrService.send_make_command()
        ↓
    ┌─────────────────────────┐
    │  Успех?                 │
    └─────────────────────────┘
        ↓                    ↓
      (да)                 (нет)
        ↓                    ↓
    Статус:              Статус:
    make_pending         make_failed
        ↓                    ↓
    Кофемашина           Логирование
    готовит              ошибки
        ↓                    ↓
    Статус:              Пользователь
    successful           видит ошибку
                         на Order Status Page
```

## Components and Interfaces

### 1. Order Model

**Файл:** `coffee_payment/payments/models.py`

**Изменения:**

Добавить новый статус `make_failed` в список допустимых статусов модели Order:

```python
class Order(models.Model):
    # ... существующие поля ...
    
    status = models.CharField(max_length=50, choices=[
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid'),
        ('make_pending', 'Make Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('make_failed', 'Make Failed'),  # НОВЫЙ СТАТУС
    ])
    
    # ... остальные поля ...
```

**Обоснование:** Статус `make_failed` является терминальным статусом, указывающим на ошибку при отправке команды приготовления. Он отличается от статуса `failed`, который используется для других критических ошибок.

### 2. Device Model

**Файл:** `coffee_payment/payments/models.py`

**Изменения:**

Добавить новое поле `client_info_make_failed` для хранения статус-специфичной информации:

```python
class Device(models.Model):
    # ... существующие поля ...
    
    client_info_make_failed = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is make_failed. Supports HTML formatting.'
    )
    
    # ... остальные поля ...
```

**Обоснование:** Поле позволяет администраторам настраивать информацию, отображаемую пользователям при статусе `make_failed`, включая контактные данные поддержки и инструкции по возврату средств.

### 3. Payment Webhook Handler

**Файл:** `coffee_payment/payments/views.py`

**Функция:** `yookassa_payment_result_webhook()`

**Изменения:**

Обернуть вызов `send_make_command()` в блок try-except для обработки ошибок:

```python
@csrf_exempt
def yookassa_payment_result_webhook(request):
    # ... существующий код валидации и обработки события ...
    
    # Только для успешных платежей продолжаем отправку команды в Tmetr API
    if event_type == 'payment.succeeded':
        # ... извлечение параметров из metadata ...
        
        tmetr_service = TmetrService()
        try:
            # Попытка отправить команду приготовления
            tmetr_service.send_make_command(
                device_id=device.device_uuid, 
                order_uuid=order_uuid, 
                drink_uuid=drink_number, 
                size=drink_size_dict[drink_size], 
                price=drink_price
            )
            
            # Успешная отправка команды
            old_status = order.status
            order.status = 'make_pending'
            order.save(update_fields=['status'])
            log_info(
                f"Order {order.id} status changed: {old_status} → make_pending. "
                f"Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, "
                f"drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}",
                'yookassa_payment_result_webhook'
            )
            
        except requests.RequestException as e:
            # Ошибка сети или API Tmetr
            old_status = order.status
            order.status = 'make_failed'
            order.save(update_fields=['status'])
            log_error(
                f"Failed to send make command for order {order.id}: {str(e)}. "
                f"Status changed: {old_status} → make_failed. "
                f"Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, "
                f"drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}",
                'yookassa_payment_result_webhook',
                'ERROR'
            )
            # Возвращаем 200, чтобы платежная система не повторяла webhook
            return HttpResponse(status=200)
            
        except Exception as e:
            # Другие непредвиденные ошибки
            old_status = order.status
            order.status = 'make_failed'
            order.save(update_fields=['status'])
            log_error(
                f"Unexpected error sending make command for order {order.id}: {str(e)}. "
                f"Status changed: {old_status} → make_failed. "
                f"Request params: device_id={device.device_uuid}, order_uuid={order_uuid}, "
                f"drink_uuid={drink_number}, size={drink_size_dict[drink_size]}, price={drink_price}",
                'yookassa_payment_result_webhook',
                'ERROR'
            )
            # Возвращаем 200, чтобы платежная система не повторяла webhook
            return HttpResponse(status=200)

    return HttpResponse(status=200)
```

**Обоснование:** 
- Обработка ошибок позволяет корректно установить статус `make_failed` вместо `failed`
- Логирование всех параметров запроса помогает в диагностике проблем
- Возврат HTTP 200 предотвращает повторные попытки webhook от платежной системы
- Разделение обработки `RequestException` и общих исключений позволяет различать сетевые ошибки и другие проблемы

### 4. User Messages

**Файл:** `coffee_payment/payments/user_messages.py`

**Изменения:**

Добавить описание статуса `make_failed` в словарь `STATUS_DESCRIPTIONS`:

```python
STATUS_DESCRIPTIONS = {
    'pending': 'Проверяем оплату заказа...',
    'paid': 'Заказ успешно оплачен, начинаем готовить',
    'not_paid': 'Оплата не прошла',
    'make_pending': 'Готовим напиток...',
    'successful': 'Напиток готов',
    'failed': 'Произошла ошибка при обработке заказа',
    'make_failed': 'Не удалось отправить команду на приготовление. Пожалуйста, обратитесь в поддержку.',  # НОВОЕ
}
```

**Обоснование:** Централизованное хранение сообщений обеспечивает единообразие текстов и упрощает их изменение.

### 5. Order Status Page (Frontend)

**Файл:** `coffee_payment/templates/payments/order_status_page.html`

**Изменения:**

#### 5.1. JavaScript - Добавление описания статуса

```javascript
// Status descriptions
const STATUS_DESCRIPTIONS = {
    'created': 'Подтвердите заказ для оплаты',
    'pending': 'Проверяем оплату заказа...',
    'paid': 'Заказ успешно оплачен, начинаем готовить',
    'not_paid': 'Оплата не прошла',
    'make_pending': 'Готовим напиток...',
    'successful': 'Напиток готов',
    'failed': 'Произошла ошибка при обработке заказа',
    'make_failed': 'Не удалось отправить команду на приготовление. Пожалуйста, обратитесь в поддержку.'  // НОВОЕ
};
```

#### 5.2. JavaScript - Обработка статуса в функции updateUI()

Добавить новый case в switch statement:

```javascript
function updateUI(orderData) {
    // ... существующий код ...
    
    // Set status icon and client info based on status
    switch (orderData.status) {
        // ... существующие cases ...
        
        case 'make_failed':  // НОВЫЙ CASE
            statusIcon.innerHTML = '⚠';
            statusIcon.className = 'status-icon error-icon';
            if (orderData.device.client_info_make_failed) {
                clientInfoText.innerHTML = orderData.device.client_info_make_failed;
                clientInfoSection.classList.remove('hidden');
            } else {
                clientInfoSection.classList.add('hidden');
            }
            paymentBtn.classList.add('hidden');
            retryBtn.classList.add('hidden');
            break;
        
        // ... остальные cases ...
    }
    
    // ... остальной код ...
}
```

#### 5.3. JavaScript - Остановка polling для терминального статуса

Обновить условие остановки polling:

```javascript
function startPolling(orderId) {
    pollingInterval = setInterval(async () => {
        try {
            const data = await fetchOrderStatus(orderId);
            updateUI(data);
            
            // Stop polling for terminal statuses and created status
            if (['created', 'successful', 'not_paid', 'failed', 'make_failed'].includes(data.status)) {  // ДОБАВЛЕН make_failed
                clearInterval(pollingInterval);
                pollingInterval = null;
                console.log('Polling stopped for terminal/created status:', data.status);
            }
        } catch (error) {
            console.error('Polling error:', error);
            // Continue polling even on error
        }
    }, 1000);
}
```

**Обоснование:**
- Статус `make_failed` является терминальным, поэтому polling должен останавливаться
- Иконка предупреждения (⚠) визуально указывает на ошибку
- Поддержка статус-специфичной информации позволяет администраторам настраивать сообщения
- Кнопки оплаты и повтора скрываются, так как заказ уже оплачен

### 6. API Endpoint для получения статуса

**Файл:** `coffee_payment/payments/views.py`

**Функция:** `get_order_status()`

**Изменения:**

Добавить поле `client_info_make_failed` в ответ API:

```python
@csrf_exempt
def get_order_status(request, order_id):
    # ... существующий код ...
    
    # Prepare response data
    data = {
        'order_id': order.id,
        'status': order.status,
        'drink_name': order.drink_name,
        'drink_size': SIZE_LABELS.get(order.size, 'неизвестный размер'),
        'price': float(order.price / 100),
        'expires_at': order.expires_at.isoformat(),
        'device': {
            'location': order.device.location,
            'logo_url': order.device.logo_url,
            'client_info': order.device.client_info,
            'client_info_pending': order.device.client_info_pending,
            'client_info_paid': order.device.client_info_paid,
            'client_info_not_paid': order.device.client_info_not_paid,
            'client_info_make_pending': order.device.client_info_make_pending,
            'client_info_successful': order.device.client_info_successful,
            'client_info_make_failed': order.device.client_info_make_failed,  # НОВОЕ ПОЛЕ
        }
    }
    
    return JsonResponse(data, status=200)
```

**Обоснование:** API должен возвращать статус-специфичную информацию для всех статусов, включая `make_failed`.

## Data Models

### Order Model Changes

```python
class Order(models.Model):
    # ... существующие поля без изменений ...
    
    status = models.CharField(max_length=50, choices=[
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid'),
        ('make_pending', 'Make Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('make_failed', 'Make Failed'),  # НОВЫЙ СТАТУС
    ])
    
    # ... остальные поля без изменений ...
```

### Device Model Changes

```python
class Device(models.Model):
    # ... существующие поля без изменений ...
    
    client_info_make_failed = models.TextField(
        null=True,
        blank=True,
        help_text='Information displayed to customers when order status is make_failed. Supports HTML formatting.'
    )
    
    # ... остальные поля без изменений ...
```

### Database Migration

Необходимо создать миграцию для:
1. Добавления нового выбора статуса в поле `Order.status`
2. Добавления нового поля `Device.client_info_make_failed`

Команда для создания миграции:
```bash
python manage.py makemigrations payments
```

Команда для применения миграции:
```bash
python manage.py migrate payments
```

## Error Handling

### Обработка ошибок в webhook

**Типы ошибок:**

1. **requests.RequestException** — ошибки сети или HTTP-запросов к Tmetr API
   - Таймауты
   - Ошибки соединения
   - HTTP ошибки (4xx, 5xx)

2. **Exception** — другие непредвиденные ошибки
   - Ошибки сериализации данных
   - Ошибки валидации
   - Внутренние ошибки Python

**Стратегия обработки:**

- Все ошибки при отправке команды приготовления приводят к установке статуса `make_failed`
- Детали ошибки логируются с уровнем ERROR
- Webhook возвращает HTTP 200 для предотвращения повторных попыток
- Пользователь видит понятное сообщение об ошибке на Order Status Page

### Логирование

**Формат логов:**

```
[timestamp] [уровень] [функция] сообщение с контекстом
```

**Примеры:**

Успешная отправка команды:
```
[2025-11-18T10:30:00+03:00] INFO [yookassa_payment_result_webhook] Order abc-123 status changed: paid → make_pending. Request params: device_id=device-uuid, order_uuid=abc-123, drink_uuid=drink-id, size=MEDIUM, price=15000
```

Ошибка отправки команды:
```
[2025-11-18T10:30:00+03:00] ERROR [yookassa_payment_result_webhook] Failed to send make command for order abc-123: Connection timeout. Status changed: paid → make_failed. Request params: device_id=device-uuid, order_uuid=abc-123, drink_uuid=drink-id, size=MEDIUM, price=15000
```

## Testing Strategy

### Unit Tests

**Файл:** `coffee_payment/tests/test_make_failed_status.py`

**Тестовые сценарии:**

1. **test_order_model_make_failed_status**
   - Проверка, что статус `make_failed` может быть установлен для заказа
   - Проверка, что статус сохраняется в базе данных

2. **test_device_model_client_info_make_failed**
   - Проверка, что поле `client_info_make_failed` может быть установлено
   - Проверка, что поле поддерживает HTML-форматирование
   - Проверка, что поле может быть пустым (null/blank)

3. **test_webhook_make_failed_on_tmetr_error**
   - Мокирование ошибки Tmetr API
   - Проверка, что статус заказа меняется на `make_failed`
   - Проверка, что webhook возвращает HTTP 200
   - Проверка логирования ошибки

4. **test_webhook_make_failed_on_unexpected_error**
   - Мокирование непредвиденной ошибки
   - Проверка, что статус заказа меняется на `make_failed`
   - Проверка, что webhook возвращает HTTP 200
   - Проверка логирования ошибки

5. **test_get_order_status_includes_make_failed_info**
   - Проверка, что API возвращает поле `client_info_make_failed`
   - Проверка корректности JSON-ответа

### Integration Tests

**Файл:** `coffee_payment/tests/test_make_failed_integration.py`

**Тестовые сценарии:**

1. **test_full_payment_flow_with_tmetr_failure**
   - Создание заказа через `process_payment_flow`
   - Инициация платежа
   - Мокирование успешного webhook от Yookassa
   - Мокирование ошибки Tmetr API
   - Проверка, что статус заказа становится `make_failed`
   - Проверка, что Order Status Page отображает корректную информацию

2. **test_order_status_page_displays_make_failed**
   - Создание заказа со статусом `make_failed`
   - Запрос к `/v1/order-status/<order_id>`
   - Проверка, что API возвращает корректные данные
   - Проверка, что статус-специфичная информация включена в ответ

### Manual Testing

**Сценарии для ручного тестирования:**

1. **Тестирование через Django Admin**
   - Создать устройство с заполненным полем `client_info_make_failed`
   - Создать заказ со статусом `make_failed`
   - Открыть Order Status Page и проверить отображение

2. **Тестирование webhook с мокированием**
   - Временно изменить код для принудительного вызова ошибки в `send_make_command`
   - Отправить тестовый webhook
   - Проверить логи и статус заказа

3. **Тестирование UI**
   - Открыть Order Status Page для заказа со статусом `make_failed`
   - Проверить отображение иконки предупреждения
   - Проверить отображение статус-специфичной информации
   - Проверить, что polling остановлен
   - Проверить, что кнопки оплаты скрыты

## Implementation Notes

### Порядок реализации

1. **Обновление моделей**
   - Добавить статус `make_failed` в Order.status
   - Добавить поле `client_info_make_failed` в Device
   - Создать и применить миграцию

2. **Обновление user_messages.py**
   - Добавить описание статуса `make_failed`

3. **Обновление webhook handler**
   - Добавить обработку ошибок в `yookassa_payment_result_webhook`
   - Добавить логирование

4. **Обновление API endpoint**
   - Добавить поле `client_info_make_failed` в ответ `get_order_status`

5. **Обновление Order Status Page**
   - Добавить описание статуса в JavaScript
   - Добавить обработку статуса в `updateUI()`
   - Обновить условие остановки polling

6. **Тестирование**
   - Написать unit tests
   - Написать integration tests
   - Провести ручное тестирование

### Обратная совместимость

- Новое поле `client_info_make_failed` является опциональным (null=True, blank=True)
- Существующие заказы не будут затронуты
- Существующие устройства будут иметь пустое значение для `client_info_make_failed`
- Миграция не требует заполнения данных

### Производительность

- Добавление нового статуса не влияет на производительность
- Обработка ошибок в webhook добавляет минимальные накладные расходы
- Polling на Order Status Page останавливается для статуса `make_failed`, что снижает нагрузку на сервер

### Безопасность

- Детали технических ошибок не отображаются пользователю
- Логирование содержит достаточно информации для диагностики без раскрытия чувствительных данных
- HTML в поле `client_info_make_failed` должен быть санитизирован администратором (ответственность администратора)

## Future Enhancements

1. **Автоматический retry механизм**
   - Добавить возможность автоматической повторной попытки отправки команды
   - Настраиваемое количество попыток и интервалы

2. **Уведомления администратора**
   - Отправка email/SMS администратору при статусе `make_failed`
   - Интеграция с системами мониторинга

3. **Возврат средств**
   - Автоматический возврат средств при статусе `make_failed`
   - Интеграция с API платежных систем для рефандов

4. **Аналитика**
   - Сбор статистики по ошибкам `make_failed`
   - Dashboard для мониторинга проблемных устройств
