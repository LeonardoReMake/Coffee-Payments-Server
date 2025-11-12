# Requirements Document

## Introduction

Данная спецификация описывает функциональность конфигурации сценариев оплаты для кофемашин в системе Coffee Payments Server. Система должна позволять каждой кофемашине (Device) использовать различные сценарии оплаты (Yookassa, TBank, Custom), а каждому мерчанту хранить свои учетные данные (Credentials) для каждого сценария. Это обеспечит гибкость в выборе платежных провайдеров и возможность интеграции с внешними системами оплаты.

## Glossary

- **Device** — кофемашина, зарегистрированная в системе
- **Merchant** — владелец одной или нескольких кофемашин
- **Payment Scenario** — сценарий оплаты, определяющий логику обработки платежа (Yookassa, TBank, Custom)
- **Credentials** — учетные данные мерчанта для конкретного сценария оплаты, хранящиеся в формате JSON
- **Order** — заказ напитка, создаваемый после валидации запроса
- **redirect_url** — URL для перенаправления пользователя при использовании сценария Custom

## Requirements

### Requirement 1

**User Story:** Как администратор системы, я хочу определить список доступных сценариев оплаты в настройках проекта, чтобы контролировать, какие платежные провайдеры могут использоваться в системе.

#### Acceptance Criteria

1. THE System SHALL store the list of available payment scenarios in project settings
2. THE System SHALL include three payment scenarios in the initial configuration: "Yookassa", "TBank", and "Custom"
3. THE System SHALL use "Yookassa" as the default payment scenario WHEN no scenario is explicitly configured for a Device
4. THE System SHALL allow administrators to modify the list of available payment scenarios through project settings

### Requirement 2

**User Story:** Как владелец кофемашины (Merchant), я хочу настроить сценарий оплаты для каждой моей кофемашины, чтобы использовать разных платежных провайдеров для разных устройств.

#### Acceptance Criteria

1. THE System SHALL allow each Device to have an assigned payment scenario
2. WHEN a Device is created without an assigned payment scenario, THE System SHALL assign the default payment scenario "Yookassa"
3. THE System SHALL validate that the assigned payment scenario exists in the list of available scenarios
4. THE System SHALL allow updating the payment scenario for an existing Device

### Requirement 3

**User Story:** Как владелец кофемашины (Merchant), я хочу хранить свои учетные данные для каждого сценария оплаты, чтобы система могла использовать их при обработке платежей.

#### Acceptance Criteria

1. THE System SHALL store Credentials for each Merchant for each payment scenario
2. THE System SHALL store Credentials in JSON format in the database
3. WHERE the payment scenario is "Yookassa", THE System SHALL expect Credentials to contain "account_id" and "secret_key" fields
4. THE System SHALL allow one Merchant to have Credentials for multiple payment scenarios
5. THE System SHALL validate that Credentials exist for a Merchant before processing a payment with the corresponding scenario

### Requirement 4

**User Story:** Как система обработки платежей, я хочу использовать соответствующие учетные данные мерчанта при выполнении сценария оплаты, чтобы платежи обрабатывались через правильный аккаунт платежного провайдера.

#### Acceptance Criteria

1. WHEN processing a payment, THE System SHALL retrieve the payment scenario assigned to the Device
2. WHEN processing a payment, THE System SHALL retrieve the Credentials for the Merchant corresponding to the payment scenario
3. WHERE the payment scenario is "Yookassa", THE System SHALL use the Merchant's Yookassa Credentials to create the payment
4. WHERE the payment scenario is "TBank", THE System SHALL use the Merchant's TBank Credentials to create the payment
5. IF Credentials are missing for the required payment scenario, THEN THE System SHALL return an error and set the Order status to "failed"

### Requirement 5

**User Story:** Как пользователь, покупающий напиток через кофемашину с Custom сценарием оплаты, я хочу быть перенаправленным на внешнюю систему оплаты, чтобы завершить платеж через стороннего провайдера.

#### Acceptance Criteria

1. WHERE the payment scenario is "Custom", WHEN an Order is created with status "created", THE System SHALL redirect the user to the redirect_url specified for the Device
2. WHERE the payment scenario is "Custom", THE System SHALL append all necessary order parameters to the redirect_url as query parameters
3. WHERE the payment scenario is "Custom", THE System SHALL validate that the Device has a non-empty redirect_url before processing the payment
4. WHERE the payment scenario is "Custom" and the Device has no redirect_url, THE System SHALL return an error and set the Order status to "failed"

### Requirement 6

**User Story:** Как разработчик, я хочу, чтобы система логировала все операции, связанные со сценариями оплаты, чтобы можно было отслеживать и отлаживать процесс обработки платежей.

#### Acceptance Criteria

1. WHEN a payment scenario is selected for a Device, THE System SHALL log the scenario name and Device identifier
2. WHEN Credentials are retrieved for a payment scenario, THE System SHALL log the Merchant identifier and scenario name
3. WHEN a payment is processed, THE System SHALL log all request parameters including the payment scenario used
4. IF an error occurs during payment processing, THE System SHALL log the error details including the payment scenario and Merchant identifier
