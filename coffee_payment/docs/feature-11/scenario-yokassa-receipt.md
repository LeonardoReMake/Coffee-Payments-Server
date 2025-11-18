Необходимо создать новый сценарий платежа YookassaReceipt, который является расширением существующего сценария Yookassa.
Этот сценарий должен отправлять в ЮKassa вместе с платежом данные для формирования фискального чека.

# Общие требования
## Название сценария
 - Новый сценарий называется: YookassaReceipt.

## Базовое поведение
 - Логика сценария должна расширять существующий сценарий Yookassa.
 - Всё, что работает в Yookassa, должно работать и здесь, дополнительно добавляется формирование объекта receipt.

# Merchant Credentials
## Хранение настроек
В Merchant Credentials для сценария YookassaReceipt необходимо хранить:
 - is_receipt_mandatory — флаг, обязательно ли пользователь должен указать email для отправки чека.
 - tax_system_code — используется при формировании чека.
 - (Опционально) timezone — используется при формировании чека.
 - (Опционально) vat_code — если в таблице Drink для напитка нет VAT-кода, брать его из Credentials.
 - (Опционально) measure — если в таблице Drink для напитка нет measure, брать его из Credentials.
 - (Опционально) payment_subject - если в таблице Drink для напитка нет payment_subject, брать его из Credentials.
 - (Опционально) payment_mode - если в таблице Drink для напитка нет payment_mode, брать его из Credentials.

Все данные хранятся в JSON без дополнительной схемы.

## Пример
```
{
  "account_id": "1193510",
  "secret_key": "test_Ku1e9ZkX...",
  "is_receipt_mandatory": true,
  "tax_system_code": 1,
  "timezone": 1,
  "vat_code": 2
}
```

# Изменения на странице статуса заказа
## Условие отображения
На странице статуса заказа (order_status_page), если сценарий = YookassaReceipt и статус заказа = created, необходимо:

## Поле для ввода email
 - Показать поле ввода email пользователя.
 - Проверять валидность email (простая валидация).
 - Если is_receipt_mandatory = true:
    - поле обязательное,
    - без заполнения кнопка «Перейти к оплате» должна быть неактивной.
 - Если is_receipt_mandatory = false:
    - поле необязательное,
    - пользователь может перейти к оплате без ввода email.

# Данные для Drink и meta
## Модель Drink
 - В модели Drink добавить поле meta (JSON), где хранятся данные для чека:
    - vat_code
    - measure
    - payment_subject
    - payment_mode
 - Изменить идентификатор Drink:
    - перевести ID с UUID на обычный integer/string ID, чтобы соответствовать входящим данным.

## Если Drink найден
Использовать данные из Drink.meta.
## Если Drink не найден
Использовать данные из Merchant Credentials:
 - В частности vat_code и возможные fallback-поля.

Если какого-либо поля нет ни в Drink, ни в Merchant Credentials, то его не нужно указывать в объекте receipt.

# Создание платежа в Yookassa (с чеком)
## Когда пользователь нажимает «Перейти к оплате»
Создаётся платёж аналогично сценарию Yookassa, но дополняется объектом receipt, если email указан.
## Формирование объекта receipt
Если пользователь указал email, при создании платежа добавить:
```
"receipt": {
    "customer": {
        "email": "[email пользователя]"
    },
    "items": [
        {
            "description": "[название напитка]",
            "amount": {
                "value": "[цена в формате 0.00]",
                "currency": "RUB"
            },
            "vat_code": [number],
            "quantity": 1,
            "measure": "[string]",
            "payment_subject": "[string]",
            "payment_mode": "[string]"
        }
    ],
    "internet": false,
    "tax_system_code": [integer],
    "timezone": [integer]
}
```

# Источники данных для формирования чека
Для массива receipt.items и других параметров чека необходимо использовать следующую схему получения значений:

## Поля уровня item:
 - vat_code
 - measure
 - payment_subject
 - payment_mode
## Логика:
 - Ищем в Drink.meta.
 - Если отсутствует — ищем в Merchant Credentials.
 - Если отсутствует в обоих — поле исключается из итогового объекта.

## Поля уровня receipt:
 - tax_system_code
 - timezone
## Логика:
 - Ищем в Merchant Credentials.
 - Если отсутствует — поле не добавляется.

# Сохранение Receipt в базу
После успешного создания платежа (если в запросе был чек):
 - Создать запись в таблице Receipt.
 - Хранить всю информацию о чеке:
    - email,
    - drink_no,
    - amount,
    - timestamp,
    - любые дополнительные поля Yookassa.

Формат хранения — JSON (MVP).

# Обновление описания проекта
Обнови описание проекта в PROJECT.md.