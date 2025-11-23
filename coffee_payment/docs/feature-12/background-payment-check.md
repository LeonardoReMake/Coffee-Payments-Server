## 1. Новый статус заказа: `manual_make`

Добавить новый статус заказа **manual_make** — статус, в котором заказ оплачен, напиток готов к приготовлению, но команда на приготовление **не отправляется автоматически**.  
Этот статус используется для старых/зависших заказов, если они оплатились спустя значительное время и клиент уже ушёл от кофемашины.

---

## 2. Добавить новые поля в модель `Order`

- `payment_started_at`: datetime | null  
  — время, когда пользователь был успешно перенаправлен в платёжную систему.

- `next_check_at`: datetime | null  
  — время следующей проверки статуса платежа.

- `last_check_at`: datetime | null  
  — время последней проверки статуса платежной системы.

- `check_attempts`: integer  
  — количество попыток проверки статуса платежа.  
  — начальное значение: **0**.

- `failed_presentation_desc`: text  
  — описание причины перевода заказа в статус `FAILED`, которое будет показано пользователю.

---

## 3. Создать фоновую задачу Celery

Запускать задачу **каждые N секунд** (значение берётся из настроек проекта).

### Основная логика фоновой задачи

#### 3.1. Получение заказов для проверки
В запрос входят все Orders:
- статус = `PENDING`
- `next_check_at` <= текущее время (и не null)
- `expires_at` > текущее время

Отсортировать по `payment_started_at`: **сначала новые, потом старые**.

Залогировать:
- количество найденных заказов в `PENDING`

---

#### 3.2. Получение контекста заказа
Для каждого Order:

1. Получить `Device`.
2. По `Device` определить платежный сценарий (`PaymentScenario`).
3. Получить `Merchant` и соответствующие `Merchant Credentials` для этого сценария.

---

#### 3.3. Получение статуса платежа в платёжной системе

##### Для сценариев:
- `Yookassa`
- `YookassaReceipt`

Отправить запрос: GET /v3/payments/{payment_id}
`payment_id` берётся из `Order.payment_reference_id`.

Требования:
- общий таймаут запроса: **3 секунды**

##### Для остальных сценариев:
- ничего не делать

---

#### 3.4. Определить статус платежа в платёжной системе
Для Yookassa-сценариев:
- взять поле `status` из ответа ЮKassa

Для остальных сценариев:
- ничего не делать

---

## 4. Обработка результата проверки

Всегда обновлять:
- `last_check_at = now()`
- `check_attempts += 1`

---

### 4.1. Ошибка сети / таймаут / исключение при запросе:

Если `check_attempts <= PAYMENT_ATTEMPTS_LIMIT`:

- оставить статус заказа прежним
- `next_check_at = now + FAST_TRACK_LIMIT_S`

Если `check_attempts > PAYMENT_ATTEMPTS_LIMIT`:

- `status = FAILED`
- `failed_presentation_desc = текст ошибки`
- `next_check_at = null`

---

### 4.2. Обработка статусов для Yookassa и YookassaReceipt

#### Статус `"pending"`
Статус заказа в БД **не изменяем**.  
Обновляем `next_check_at`:

- если `now - payment_started_at <= FAST_TRACK_LIMIT_S`  
  → `next_check_at = now + FAST_TRACK_INTERVAL_S` (быстрая проверка)

- если `now - payment_started_at > FAST_TRACK_LIMIT_S`  
  → `next_check_at = now + SLOW_TRACK_INTERVAL_S` (медленная проверка)

---

#### Статус `"succeeded"`
Статус заказа обновляется на **PAID**.

- если `now - payment_started_at <= FAST_TRACK_LIMIT_S`:
  - **отправить команду приготовления в TMetr API**
    (по аналогии с обработкой успешного webhook Yookassa)
  - `next_check_at = null`

- если `now - payment_started_at > FAST_TRACK_LIMIT_S`:
  - переводим заказ в статус **manual_make**
  - `next_check_at = null`

---

#### Статус `"canceled"`
- статус = **NOT_PAID**
- `next_check_at = null`

---

#### Статус `"waiting_for_capture"`
- статус = **FAILED**
- `next_check_at = null`

---

### 4.3. Для остальных платежных сценариев
Ничего не делаем.

---

## 5. Пример получения платежа в Yookassa

```python
from yookassa import Payment

payment_id = order.payment_reference_id
payment = Payment.find_one(payment_id)
```
Таймаут запроса: 3 секунды.

---

## 6. Обновить webhook Yookassa
Необходимо обновить обработку webhook Yookassa:
 - логику обработки статусов succeeded и canceled
 - сделать её аналогичной логике фоновой задачи (описанной выше)
Webhook должен корректно:
 - отправлять команду в TMetr API (если быстрый платёж)
 - переводить заказ в manual_make (если просроченный платёж)
 - корректно обновлять статусы NOT_PAID, FAILED и т.д.

---

## 7. Обновить описание проекта в PROJECT.md
 - обнови описание проекта в PROJECT.md
 - при разработке прочитай обновленные требования из CONSTITUTION.md
 - не создавай дополнительных описаний