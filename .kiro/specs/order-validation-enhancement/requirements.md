# Requirements Document

## Introduction

This feature enhances the order validation process in the coffee payment system by adding multiple validation steps after QR code scanning and before payment scenario execution. The goal is to strengthen request correctness control and equipment state verification before initiating payment processing. All validations execute sequentially with early termination on first error, displaying user-friendly error screens when validation fails.

## Glossary

- **Payment System**: The coffee payment server that processes orders and payments for coffee machines
- **QR Code**: Quick Response code displayed on coffee machines that users scan to initiate payment
- **Order**: A record in the database representing a drink purchase request with status tracking
- **Device**: A coffee machine registered in the system with UUID identifier
- **Tmetr API**: External telemetry service API that provides device status and drink information
- **Heartbeat**: Periodic status signal from coffee machine indicating it is online and operational
- **Request Hash**: Cryptographic hash value used to verify request integrity and authenticity
- **Validation Chain**: Sequential execution of validation checks with early termination on failure
- **Loading Screen**: User interface state showing validation is in progress
- **Error Screen**: User interface displaying user-friendly error message when validation fails
- **User Messages File**: Centralized file (user_messages.py) containing all user-facing error messages

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want request hash validation to execute first in the validation chain, so that only authentic requests from legitimate QR codes are processed

#### Acceptance Criteria

1. WHEN THE Payment System receives a payment request, THE Payment System SHALL validate the request hash before any other validation steps
2. IF the request hash validation fails, THEN THE Payment System SHALL display an error screen to the user and terminate the validation chain
3. THE Payment System SHALL provide a placeholder implementation for hash validation that can be completed later
4. THE Payment System SHALL log all hash validation attempts with request parameters

### Requirement 2

**User Story:** As a customer, I want the system to check if my order already exists, so that I can resume an existing order without creating duplicates

#### Acceptance Criteria

1. WHEN THE Payment System validates a request, THE Payment System SHALL check if an order with the provided UUID exists in the database
2. IF an order exists with status "created" and has not expired, THEN THE Payment System SHALL continue the payment scenario without creating a new order
3. IF an order exists but has expired based on the expires_at field, THEN THE Payment System SHALL display an error screen and terminate the validation chain
4. IF no order exists with the provided UUID, THEN THE Payment System SHALL proceed to create a new order following the standard process
5. THE Payment System SHALL log all order existence check results with order UUID and status

### Requirement 3

**User Story:** As a customer, I want the system to verify the coffee machine is online before I pay, so that I don't pay for a drink that cannot be prepared

#### Acceptance Criteria

1. WHEN THE Payment System validates device status, THE Payment System SHALL send a POST request to Tmetr API heartbeat endpoint with the device UUID
2. THE Payment System SHALL include X-TimeZoneOffset header with the server timezone in the Tmetr API request
3. WHEN THE Payment System receives heartbeat data, THE Payment System SHALL calculate the time difference between current time and heartbeatCreatedAt timestamp
4. IF the time difference exceeds the configured threshold in minutes, THEN THE Payment System SHALL consider the device offline and display an error screen
5. IF the time difference is within the configured threshold, THEN THE Payment System SHALL consider the device online and continue validation
6. THE Payment System SHALL log all device status checks with device UUID, heartbeat timestamp, and online/offline determination
7. THE Payment System SHALL handle Tmetr API errors by logging the error and displaying an error screen to the user

### Requirement 4

**User Story:** As a customer, I want to see a loading screen while validations are running, so that I know the system is processing my request

#### Acceptance Criteria

1. WHEN THE Payment System begins validation chain execution, THE Payment System SHALL display a loading screen to the user
2. THE Payment System SHALL maintain the loading screen display until all validations complete successfully or a validation fails
3. WHEN a validation fails, THE Payment System SHALL transition from loading screen to error screen
4. WHEN all validations succeed, THE Payment System SHALL transition from loading screen to the appropriate next step in the payment flow

### Requirement 5

**User Story:** As a customer, I want to see clear error messages when something goes wrong, so that I understand what happened without seeing technical details

#### Acceptance Criteria

1. WHEN THE Payment System displays an error screen, THE Payment System SHALL retrieve the error message from the centralized user messages file
2. THE Payment System SHALL NOT display technical details such as stack traces, error codes, or exception messages to users
3. THE Payment System SHALL display error messages in a mobile-first responsive design that works across all device screen sizes
4. THE Payment System SHALL log technical error details for debugging while showing user-friendly messages to customers

### Requirement 6

**User Story:** As a system administrator, I want to configure the device online threshold, so that I can adjust sensitivity based on network conditions

#### Acceptance Criteria

1. THE Payment System SHALL read the device online threshold value from Django settings configuration
2. THE Payment System SHALL use the configured threshold value when determining if a device is online or offline
3. THE Payment System SHALL provide a default threshold value if no configuration is specified
4. THE Payment System SHALL log the configured threshold value at application startup

### Requirement 7

**User Story:** As a developer, I want comprehensive logging of all validation steps, so that I can debug issues and monitor system behavior

#### Acceptance Criteria

1. THE Payment System SHALL log the start of validation chain execution with all request parameters
2. THE Payment System SHALL log each validation step execution with relevant data
3. THE Payment System SHALL log validation success or failure for each step
4. THE Payment System SHALL log the final outcome of the validation chain
5. THE Payment System SHALL include timestamps and timezone information in all log entries
