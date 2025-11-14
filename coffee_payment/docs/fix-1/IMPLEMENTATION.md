# Исправление: Сохранение drink_number в заказе

## Проблема

При обработке заказа система не сохраняла `drink_number` (ID напитка на устройстве) из QR-кода в модели Order. Из-за этого при передаче `drink_details` в сценарий оплаты вместо реального `drink_id` передавалось значение "unknown".

## Решение

### 1. Добавлено поле drink_number в модель Order

**Файл:** `coffee_payment/payments/models.py`

```python
class Order(models.Model):
    # ... существующие поля ...
    drink_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Drink ID at the device (drinkNo from QR code)'
    )
```

### 2. Создана миграция базы данных

**Файл:** `coffee_payment/payments/migrations/0017_order_drink_number.py`

Миграция добавляет новое поле `drink_number` в таблицу Order с поддержкой NULL значений для обратной совместимости.

### 3. Обновлена логика создания заказа

**Файл:** `coffee_payment/payments/views.py`

При создании нового заказа в функции `process_payment_flow()` теперь сохраняется `drink_number` из параметров запроса:

```python
order = Order.objects.create(
    id=order_uuid,
    drink_name=drink_name,
    drink_number=drink_number,  # НОВОЕ: сохраняем drink_number
    device=device,
    merchant=merchant,
    size=drink_size_int,
    price=drink_price,
    status='created'
)
```

### 4. Обновлена реконструкция drink_details

**Файл:** `coffee_payment/payments/views.py`

В функции `initiate_payment()` при реконструкции `drink_details` из существующего заказа теперь используется сохраненный `drink_number`:

```python
drink_details = {
    'price': int(order.price),
    'name': order.drink_name,
    'drink_id': order.drink_number if order.drink_number else 'unknown',  # ИСПРАВЛЕНО
}
```

### 5. Обновлена документация проекта

**Файл:** `coffee_payment/docs/PROJECT.md`

Добавлено упоминание о сохранении `drink_number` в описании модели Order.

## Результат

Теперь система корректно:
1. Сохраняет `drink_number` из QR-кода при создании заказа
2. Передает реальный `drink_id` в платежные сценарии (Yookassa, TBank)
3. Использует корректный `drink_number` в webhook'ах и при отправке команд в Tmetr API

## Обратная совместимость

- Поле `drink_number` имеет `null=True, blank=True`, поэтому существующие заказы без этого поля продолжат работать
- Все существующие тесты продолжают работать без изменений
- При отсутствии `drink_number` в заказе используется fallback значение "unknown"

## Миграция

Для применения изменений необходимо выполнить миграцию базы данных:

```bash
python manage.py migrate payments
```
