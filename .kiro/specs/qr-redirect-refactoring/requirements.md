# Requirements Document

## Introduction

Данная спецификация описывает рефакторинг логики обработки QR-кодов в системе Coffee Payments Server. Текущая реализация имеет несоответствие: при сканировании QR-кода пользователь переходит на `/v1/pay` → `qr_code_redirect` → редирект на `Device.redirect_url`, но отсутствует логика определения платежного сценария, которая реализована в `yookassa_payment_process`. Необходимо объединить эти функции и переименовать `yookassa_payment_process` в более общее название, так как она обрабатывает не только сценарий Yookassa.

## Glossary

- **QR System** — система обработки QR-кодов, сканируемых пользователями с кофемашин
- **Payment Scenario** — сценарий оплаты (Yookassa, TBank, Custom), настроенный для конкретного устройства
- **Device** — кофемашина, зарегистрированная в системе
- **Order** — заказ напитка, создаваемый после валидации QR-кода
- **Merchant** — владелец кофемашины
- **Payment Process View** — view-функция для обработки платежного процесса (текущее название: `yookassa_payment_process`)

## Requirements

### Requirement 1

**User Story:** Как пользователь, я хочу, чтобы при сканировании QR-кода система автоматически определяла правильный платежный сценарий, чтобы я мог оплатить напиток через соответствующую платежную систему.

#### Acceptance Criteria

1. WHEN пользователь сканирует QR-код с кофемашины, THE QR System SHALL валидировать параметры запроса (deviceUuid, drinkNo, size, uuid)
2. WHEN валидация параметров успешна, THE QR System SHALL проверить существование Device и активность Merchant
3. WHEN Device и Merchant валидны, THE QR System SHALL определить Payment Scenario для данного Device
4. WHEN Payment Scenario определен, THE QR System SHALL инициировать процесс создания Order и обработки платежа согласно выбранному сценарию
5. IF параметры запроса отсутствуют или некорректны, THEN THE QR System SHALL вернуть страницу ошибки с HTTP статусом 400

### Requirement 2

**User Story:** Как разработчик, я хочу, чтобы функция обработки платежей имела общее название, не привязанное к конкретной платежной системе, чтобы код был понятным и поддерживаемым.

#### Acceptance Criteria

1. THE QR System SHALL переименовать функцию `yookassa_payment_process` в `process_payment_flow`
2. THE QR System SHALL обновить все ссылки на старое имя функции в URL-конфигурации
3. THE QR System SHALL обновить все логи, использующие старое имя функции
4. THE QR System SHALL сохранить всю существующую функциональность после переименования
5. THE QR System SHALL обеспечить обратную совместимость URL-эндпоинтов путем создания алиаса для старого URL

### Requirement 3

**User Story:** Как пользователь, я хочу, чтобы при сканировании QR-кода система сразу переходила к процессу оплаты, без лишних редиректов, чтобы процесс был быстрым и удобным.

#### Acceptance Criteria

1. WHEN пользователь переходит по URL `/v1/pay` с параметрами QR-кода, THE QR System SHALL напрямую вызывать логику обработки платежного процесса
2. THE QR System SHALL удалить промежуточный редирект на `Device.redirect_url` из функции `qr_code_redirect`
3. THE QR System SHALL интегрировать логику валидации из `qr_code_service` в основной платежный процесс
4. THE QR System SHALL получать информацию о напитке через Tmetr API перед созданием Order
5. THE QR System SHALL создавать Order со статусом 'created' после успешной валидации

### Requirement 4

**User Story:** Как администратор системы, я хочу, чтобы все операции обработки QR-кодов логировались с полными параметрами запроса, чтобы я мог отслеживать и отлаживать проблемы.

#### Acceptance Criteria

1. WHEN QR System обрабатывает QR-код, THE QR System SHALL логировать все входящие параметры запроса
2. WHEN QR System определяет Payment Scenario, THE QR System SHALL логировать выбранный сценарий и device_uuid
3. WHEN QR System создает Order, THE QR System SHALL логировать ID заказа, статус и параметры напитка
4. IF возникает ошибка на любом этапе, THEN THE QR System SHALL логировать детали ошибки с контекстом (device_uuid, параметры запроса)
5. THE QR System SHALL использовать существующий централизованный логгер из `payments.utils.logging`

### Requirement 5

**User Story:** Как пользователь, я хочу видеть понятные сообщения об ошибках на русском языке, когда что-то идет не так, чтобы я понимал, что произошло.

#### Acceptance Criteria

1. WHEN возникает ошибка валидации параметров, THE QR System SHALL отображать сообщение из централизованного хранилища `user_messages.py`
2. WHEN Device не найдено, THE QR System SHALL отображать сообщение "Устройство не найдено" с HTTP статусом 404
3. WHEN права Merchant истекли, THE QR System SHALL отображать сообщение "Доступ запрещен" с HTTP статусом 403
4. WHEN сервис Tmetr недоступен, THE QR System SHALL отображать сообщение "Сервис временно недоступен" с HTTP статусом 503
5. THE QR System SHALL не отображать технические детали ошибок (стек-трейсы, внутренние сообщения) пользователю
