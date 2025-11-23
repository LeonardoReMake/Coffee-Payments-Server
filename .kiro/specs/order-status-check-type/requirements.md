# Requirements Document

## Introduction

Данная фича добавляет гибкую настройку способа проверки статуса платежей в системе кофейных автоматов. Система должна поддерживать три типа проверки статуса заказа: polling (фоновый опрос платежной системы), webhook (получение уведомлений от платежной системы) и none (без автоматической проверки). Это позволит мерчантам выбирать оптимальный способ интеграции с различными платежными системами в зависимости от их возможностей и требований.

## Glossary

- **System** — сервер обработки платежей для кофейных автоматов
- **Merchant** — владелец кофемашин
- **MerchantCredentials** — учетные данные мерчанта для конкретного платежного сценария
- **Order** — заказ напитка с информацией о платеже
- **Payment Scenario** — сценарий оплаты (Yookassa, TBank, Custom)
- **Polling** — способ проверки статуса путем периодического опроса платежной системы
- **Webhook** — способ проверки статуса через получение уведомлений от платежной системы
- **Celery Task** — фоновая задача для обработки платежей
- **status_check_type** — тип проверки статуса заказа

## Requirements

### Requirement 1

**User Story:** Как администратор системы, я хочу настраивать тип проверки статуса платежей для каждого платежного сценария мерчанта, чтобы система могла интегрироваться с различными платежными системами оптимальным способом.

#### Acceptance Criteria

1. WHEN a MerchantCredentials record is created or updated THEN the System SHALL store a status_check_type field with one of three values: 'polling', 'webhook', or 'none'
2. WHEN status_check_type is not explicitly provided THEN the System SHALL use 'polling' as the default value
3. WHEN retrieving MerchantCredentials THEN the System SHALL return the status_check_type field along with other credential data
4. WHEN validating status_check_type THEN the System SHALL reject any values other than 'polling', 'webhook', or 'none'

### Requirement 2

**User Story:** Как система обработки платежей, я хочу фиксировать тип проверки статуса для каждого заказа при его создании, чтобы изменения в настройках мерчанта не влияли на уже созданные заказы.

#### Acceptance Criteria

1. WHEN an Order is created with a payment THEN the System SHALL copy the status_check_type value from the associated MerchantCredentials to the Order
2. WHEN an Order's status_check_type is set THEN the System SHALL preserve this value for the lifetime of the Order
3. WHEN MerchantCredentials are updated THEN the System SHALL NOT modify the status_check_type of existing Orders
4. WHEN retrieving Order data THEN the System SHALL include the status_check_type field

### Requirement 3

**User Story:** Как фоновая задача проверки платежей, я хочу обрабатывать только заказы с типом проверки 'polling', чтобы не дублировать проверки для заказов, обрабатываемых через webhook или не требующих проверки.

#### Acceptance Criteria

1. WHEN the Celery background task selects Orders for status checking THEN the System SHALL include only Orders where status_check_type equals 'polling'
2. WHEN the Celery background task selects Orders for status checking THEN the System SHALL exclude Orders where status_check_type equals 'webhook'
3. WHEN the Celery background task selects Orders for status checking THEN the System SHALL exclude Orders where status_check_type equals 'none'
4. WHEN filtering Orders for background checking THEN the System SHALL also apply existing filters (status='pending', next_check_at < now, expires_at > now)

### Requirement 4

**User Story:** Как разработчик, я хочу иметь актуальную документацию о типах проверки статуса заказов, чтобы понимать архитектуру системы и правильно использовать новую функциональность.

#### Acceptance Criteria

1. WHEN the feature is implemented THEN the System SHALL have updated PROJECT.md documentation describing the status_check_type field
2. WHEN the feature is implemented THEN the documentation SHALL explain all three status_check_type values and their behavior
3. WHEN the feature is implemented THEN the documentation SHALL describe how status_check_type affects background payment checking
4. WHEN the feature is implemented THEN the documentation SHALL follow the principles defined in CONSTITUTION.md
