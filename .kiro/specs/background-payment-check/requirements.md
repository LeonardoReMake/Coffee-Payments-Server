# Requirements Document

## Introduction

This feature implements a background payment status checking system for the Coffee Payments Server. The system addresses the problem of delayed payment confirmations where webhooks may fail or arrive late, causing customers to wait unnecessarily at coffee machines. The background checker periodically polls payment provider APIs to verify payment status and automatically processes successful payments, while also handling edge cases where customers have left the machine before payment completion.

## Glossary

- **System**: The Coffee Payments Server application
- **Background Task**: A Celery periodic task that runs independently of HTTP requests
- **Payment Provider**: External payment service (Yookassa, YookassaReceipt)
- **Order**: A coffee order record in the database with status tracking
- **Fast Track**: Quick payment completion within configured time limit
- **Slow Track**: Delayed payment completion beyond fast track limit
- **Manual Make Status**: Order status indicating payment succeeded but drink preparation requires manual intervention
- **TMetr API**: External API for controlling coffee machines

## Requirements

### Requirement 1

**User Story:** As a system operator, I want orders to have additional tracking fields, so that the system can monitor payment check progress and handle failures appropriately.

#### Acceptance Criteria

1. WHEN an Order is created THEN the System SHALL initialize check_attempts field to zero
2. WHEN a user is redirected to a Payment Provider THEN the System SHALL record payment_started_at timestamp with timezone
3. WHEN the System schedules a payment check THEN the System SHALL set next_check_at timestamp with timezone
4. WHEN the System completes a payment check THEN the System SHALL update last_check_at timestamp with timezone
5. WHEN an Order transitions to failed status THEN the System SHALL store failed_presentation_desc text for user display

### Requirement 2

**User Story:** As a system operator, I want a new manual_make order status, so that delayed payments can be handled without automatic drink preparation when customers have left.

#### Acceptance Criteria

1. WHEN an Order payment succeeds after the fast track limit THEN the System SHALL transition the Order to manual_make status
2. WHEN an Order is in manual_make status THEN the System SHALL NOT send drink preparation commands to TMetr API
3. WHEN an Order transitions to manual_make status THEN the System SHALL set next_check_at to null

### Requirement 3

**User Story:** As a system operator, I want a background task to check pending payment statuses, so that payments are processed even when webhooks fail or are delayed.

#### Acceptance Criteria

1. WHEN the Background Task executes THEN the System SHALL query Orders with status pending AND next_check_at less than or equal to current time AND expires_at greater than current time
2. WHEN the Background Task retrieves Orders THEN the System SHALL sort results by payment_started_at with newest first
3. WHEN the Background Task processes an Order THEN the System SHALL increment check_attempts by one
4. WHEN the Background Task processes an Order THEN the System SHALL update last_check_at to current timestamp with timezone
5. WHEN the Background Task completes processing THEN the System SHALL log the count of Orders found in pending status

### Requirement 4

**User Story:** As a system operator, I want the background task to query payment provider APIs, so that current payment status can be retrieved independently of webhooks.

#### Acceptance Criteria

1. WHEN the Background Task processes an Order with Yookassa scenario THEN the System SHALL send GET request to Yookassa API with payment_reference_id
2. WHEN the Background Task processes an Order with YookassaReceipt scenario THEN the System SHALL send GET request to Yookassa API with payment_reference_id
3. WHEN the Background Task sends API requests THEN the System SHALL apply three second timeout
4. WHEN the Background Task processes an Order with other scenarios THEN the System SHALL skip payment status check
5. WHEN the Background Task sends API requests THEN the System SHALL log all request parameters

### Requirement 5

**User Story:** As a system operator, I want the system to handle network errors gracefully, so that temporary failures do not cause orders to fail prematurely.

#### Acceptance Criteria

1. WHEN a payment status check encounters network error AND check_attempts is less than or equal to PAYMENT_ATTEMPTS_LIMIT THEN the System SHALL maintain current Order status
2. WHEN a payment status check encounters network error AND check_attempts is less than or equal to PAYMENT_ATTEMPTS_LIMIT THEN the System SHALL set next_check_at to current time plus FAST_TRACK_INTERVAL_S
3. WHEN a payment status check encounters network error AND check_attempts exceeds PAYMENT_ATTEMPTS_LIMIT THEN the System SHALL transition Order to failed status
4. WHEN a payment status check encounters network error AND check_attempts exceeds PAYMENT_ATTEMPTS_LIMIT THEN the System SHALL set failed_presentation_desc to error message
5. WHEN a payment status check encounters network error AND check_attempts exceeds PAYMENT_ATTEMPTS_LIMIT THEN the System SHALL set next_check_at to null

### Requirement 6

**User Story:** As a system operator, I want the system to handle pending payment status, so that orders continue to be checked until payment completes or times out.

#### Acceptance Criteria

1. WHEN Payment Provider returns pending status AND time since payment_started_at is less than or equal to FAST_TRACK_LIMIT_S THEN the System SHALL set next_check_at to current time plus FAST_TRACK_INTERVAL_S
2. WHEN Payment Provider returns pending status AND time since payment_started_at exceeds FAST_TRACK_LIMIT_S THEN the System SHALL set next_check_at to current time plus SLOW_TRACK_INTERVAL_S
3. WHEN Payment Provider returns pending status THEN the System SHALL maintain Order status as pending

### Requirement 7

**User Story:** As a customer, I want my payment to be processed quickly when I complete it promptly, so that I receive my drink without unnecessary delay.

#### Acceptance Criteria

1. WHEN Payment Provider returns succeeded status AND time since payment_started_at is less than or equal to FAST_TRACK_LIMIT_S THEN the System SHALL transition Order to paid status
2. WHEN Payment Provider returns succeeded status AND time since payment_started_at is less than or equal to FAST_TRACK_LIMIT_S THEN the System SHALL send drink preparation command to TMetr API
3. WHEN Payment Provider returns succeeded status AND time since payment_started_at is less than or equal to FAST_TRACK_LIMIT_S THEN the System SHALL set next_check_at to null

### Requirement 8

**User Story:** As a system operator, I want delayed successful payments to be marked for manual handling, so that drinks are not prepared when customers have already left.

#### Acceptance Criteria

1. WHEN Payment Provider returns succeeded status AND time since payment_started_at exceeds FAST_TRACK_LIMIT_S THEN the System SHALL transition Order to manual_make status
2. WHEN Payment Provider returns succeeded status AND time since payment_started_at exceeds FAST_TRACK_LIMIT_S THEN the System SHALL set next_check_at to null
3. WHEN Payment Provider returns succeeded status AND time since payment_started_at exceeds FAST_TRACK_LIMIT_S THEN the System SHALL NOT send drink preparation command to TMetr API

### Requirement 9

**User Story:** As a system operator, I want canceled payments to be marked appropriately, so that order status accurately reflects payment failure.

#### Acceptance Criteria

1. WHEN Payment Provider returns canceled status THEN the System SHALL transition Order to not_paid status
2. WHEN Payment Provider returns canceled status THEN the System SHALL set next_check_at to null

### Requirement 10

**User Story:** As a system operator, I want waiting_for_capture payments to be marked as failed, so that orders requiring manual capture are flagged for attention.

#### Acceptance Criteria

1. WHEN Payment Provider returns waiting_for_capture status THEN the System SHALL transition Order to failed status
2. WHEN Payment Provider returns waiting_for_capture status THEN the System SHALL set next_check_at to null

### Requirement 11

**User Story:** As a system operator, I want webhook handlers to use the same payment processing logic as the background task, so that payment handling is consistent regardless of notification method.

#### Acceptance Criteria

1. WHEN Yookassa webhook receives succeeded status AND time since payment_started_at is less than or equal to FAST_TRACK_LIMIT_S THEN the System SHALL send drink preparation command to TMetr API
2. WHEN Yookassa webhook receives succeeded status AND time since payment_started_at exceeds FAST_TRACK_LIMIT_S THEN the System SHALL transition Order to manual_make status
3. WHEN Yookassa webhook receives canceled status THEN the System SHALL transition Order to not_paid status
4. WHEN Yookassa webhook receives waiting_for_capture status THEN the System SHALL transition Order to failed status
5. WHEN Yookassa webhook processes payment status THEN the System SHALL apply the same time-based logic as Background Task
