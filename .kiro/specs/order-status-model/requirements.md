# Requirements Document

## Introduction

Данная спецификация описывает изменение статусной модели заказа в системе Coffee Payments Server. Текущая модель заказа имеет упрощенные статусы (created, pending, failed, success), которые не отражают полный жизненный цикл заказа от создания до успешного приготовления напитка. Новая модель должна включать детализированные статусы для отслеживания каждого этапа обработки заказа, а также механизм автоматического протухания заказов по истечении заданного времени.

## Glossary

- **Order System** — система управления заказами в Coffee Payments Server
- **Payment Gateway** — платежная система (ЮKassa или ТБанк) для обработки платежей
- **Tmetr API** — внешний API для отправки команд приготовления напитков на кофемашины
- **Order Expiration Time** — время протухания заказа, задаваемое в настройках проекта
- **Order Status** — текущее состояние заказа в системе
- **Webhook** — уведомление от платежной системы о результате оплаты

## Requirements

### Requirement 1

**User Story:** Как система обработки заказов, я хочу создавать заказ в статусе Created после успешной валидации, чтобы зафиксировать начало обработки заказа

#### Acceptance Criteria

1. WHEN все первичные валидации пройдены успешно, THE Order System SHALL создать новый заказ со статусом Created
2. THE Order System SHALL сохранить время создания заказа в поле created_at с указанием таймзоны
3. THE Order System SHALL присвоить заказу уникальный идентификатор UUID

### Requirement 2

**User Story:** Как система обработки платежей, я хочу изменять статус заказа на Pending после создания платежа, чтобы отслеживать заказы, ожидающие оплаты

#### Acceptance Criteria

1. WHEN платеж успешно создан в Payment Gateway, THE Order System SHALL изменить статус заказа с Created на Pending
2. THE Order System SHALL сохранить идентификатор платежа в поле external_order_id
3. THE Order System SHALL обновить поле updated_at с указанием таймзоны

### Requirement 3

**User Story:** Как система обработки платежей, я хочу изменять статус заказа на Paid или Not Paid в зависимости от результата оплаты, чтобы различать успешные и неуспешные платежи

#### Acceptance Criteria

1. WHEN получено уведомление об успешной оплате через Webhook, THE Order System SHALL изменить статус заказа с Pending на Paid
2. WHEN получено уведомление о неуспешной оплате через Webhook, THE Order System SHALL изменить статус заказа с Pending на Not Paid
3. THE Order System SHALL обновить поле updated_at с указанием таймзоны при изменении статуса

### Requirement 4

**User Story:** Как система управления кофемашинами, я хочу изменять статус заказа на Make Pending после отправки команды приготовления, чтобы отслеживать заказы в процессе приготовления

#### Acceptance Criteria

1. WHEN запрос на приготовление напитка успешно отправлен в Tmetr API, THE Order System SHALL изменить статус заказа с Paid на Make Pending
2. THE Order System SHALL обновить поле updated_at с указанием таймзоны
3. THE Order System SHALL логировать параметры отправленного запроса в Tmetr API

### Requirement 5

**User Story:** Как система обработки заказов, я хочу переводить заказ в статус Failed при возникновении критических ошибок, чтобы идентифицировать заказы, которые не могут быть завершены успешно

#### Acceptance Criteria

1. WHEN в процессе обработки заказа возникает критическая ошибка, THE Order System SHALL изменить статус заказа на Failed
2. THE Order System SHALL логировать причину перехода в статус Failed
3. THE Order System SHALL обновить поле updated_at с указанием таймзоны

### Requirement 6

**User Story:** Как система обработки заказов, я хочу иметь финальный статус Successful для успешно завершенных заказов, чтобы отличать их от заказов в процессе обработки

#### Acceptance Criteria

1. THE Order System SHALL поддерживать статус Successful для заказов, успешно завершивших полный цикл обработки
2. THE Order System SHALL обновить поле updated_at с указанием таймзоны при переходе в статус Successful

### Requirement 7

**User Story:** Как администратор системы, я хочу настраивать время протухания заказов через конфигурацию проекта, чтобы контролировать жизненный цикл заказов без изменения кода

#### Acceptance Criteria

1. THE Order System SHALL читать значение времени протухания заказа из настроек проекта settings.py
2. THE Order System SHALL использовать значение в минутах для расчета времени протухания
3. WHERE параметр не задан в настройках, THE Order System SHALL использовать значение по умолчанию 15 минут

### Requirement 8

**User Story:** Как система обработки заказов, я хочу хранить время протухания для каждого заказа, чтобы определять, когда заказ становится недействительным

#### Acceptance Criteria

1. THE Order System SHALL добавить поле expires_at в модель Order
2. THE Order System SHALL рассчитывать значение expires_at как created_at плюс Order Expiration Time при создании заказа
3. THE Order System SHALL сохранять время протухания с указанием таймзоны

### Requirement 9

**User Story:** Как система обработки заказов, я хочу проверять актуальность заказа перед обработкой, чтобы не обрабатывать протухшие заказы

#### Acceptance Criteria

1. THE Order System SHALL предоставить метод is_expired для проверки протухания заказа
2. WHEN текущее время больше expires_at, THE Order System SHALL возвращать True из метода is_expired
3. WHEN текущее время меньше или равно expires_at, THE Order System SHALL возвращать False из метода is_expired
