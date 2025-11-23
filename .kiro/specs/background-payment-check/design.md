# Design Document

## Overview

This design implements a background payment status checking system using Celery periodic tasks. The system addresses webhook reliability issues by actively polling payment provider APIs to verify payment status. It introduces intelligent scheduling with fast and slow track checking intervals, handles network failures gracefully, and implements a new `manual_make` status for delayed payments where customers have likely left the coffee machine.

The design follows the MVP principle with minimal complexity while ensuring reliable payment processing. It reuses existing service patterns and integrates seamlessly with the current order status model.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Celery Beat Scheduler                     │
│              (Triggers every N seconds)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Background Payment Check Task                   │
│                  (Celery Worker)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Payment Status Service                          │
│  - Query pending orders                                      │
│  - Call payment provider APIs                                │
│  - Apply time-based logic (fast/slow track)                  │
│  - Update order status                                       │
│  - Trigger drink preparation (if applicable)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌──────────────────┐         ┌──────────────────┐
│  Yookassa API    │         │   TMetr API      │
│  (Payment Status)│         │  (Make Command)  │
└──────────────────┘         └──────────────────┘
```

### Integration Points

1. **Database**: Extended Order model with new tracking fields
2. **Celery**: New periodic task for background checking
3. **Yookassa API**: Payment status retrieval
4. **TMetr API**: Drink preparation commands (reused from existing webhook logic)
5. **Webhook Handler**: Updated to use shared payment processing logic

## Components and Interfaces

### 1. Extended Order Model

**Location**: `coffee_payment/payments/models.py`

**New Fields**:
```python
class Order(models.Model):
    # ... existing fields ...
    
    # New fields for background payment checking
    payment_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when user was redirected to payment provider (with timezone)'
    )
    next_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp for next payment status check (with timezone)'
    )
    last_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last payment status check (with timezone)'
    )
    check_attempts = models.IntegerField(
        default=0,
        help_text='Number of payment status check attempts'
    )
    failed_presentation_desc = models.TextField(
        null=True,
        blank=True,
        help_text='User-friendly description of failure reason'
    )
    
    # New status choice
    status = models.CharField(max_length=50, choices=[
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid'),
        ('make_pending', 'Make Pending'),
        ('manual_make', 'Manual Make'),  # NEW
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('make_failed', 'Make Failed'),
    ])
```

### 2. Payment Status Service

**Location**: `coffee_payment/payments/services/payment_status_service.py`

**Purpose**: Centralized logic for checking payment status and updating orders

**Interface**:
```python
class PaymentStatusService:
    """Service for checking and processing payment status"""
    
    @staticmethod
    def check_payment_status(order: Order) -> dict:
        """
        Check payment status for an order.
        
        Args:
            order: Order instance to check
            
        Returns:
            dict with keys:
                - 'status': Payment status from provider ('pending', 'succeeded', 'canceled', 'waiting_for_capture')
                - 'error': Error message if check failed (None if successful)
        """
        
    @staticmethod
    def process_payment_status(order: Order, payment_status: str) -> None:
        """
        Process payment status and update order accordingly.
        Applies time-based logic for fast/slow track.
        
        Args:
            order: Order instance to process
            payment_status: Status from payment provider
        """
        
    @staticmethod
    def handle_check_error(order: Order, error_message: str) -> None:
        """
        Handle payment check error with retry logic.
        
        Args:
            order: Order instance
            error_message: Error description
        """
```

### 3. Background Check Task

**Location**: `coffee_payment/payments/tasks.py`

**Purpose**: Celery periodic task that checks pending orders

**Interface**:
```python
@shared_task
def check_pending_payments():
    """
    Background task to check payment status for pending orders.
    Runs periodically based on CELERY_BEAT_SCHEDULE configuration.
    """
```

### 4. Celery Configuration

**Location**: `coffee_payment/coffee_payment/celery.py`

**Purpose**: Configure Celery app and beat schedule

### 5. Updated Webhook Handler

**Location**: `coffee_payment/payments/views.py`

**Changes**: Refactor `yookassa_payment_result_webhook()` to use `PaymentStatusService.process_payment_status()`

## Data Models

### Order Model Extensions

**New Fields**:

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| payment_started_at | DateTimeField | Yes | NULL | When user was redirected to payment provider |
| next_check_at | DateTimeField | Yes | NULL | When to perform next status check |
| last_check_at | DateTimeField | Yes | NULL | When last status check was performed |
| check_attempts | IntegerField | No | 0 | Number of check attempts made |
| failed_presentation_desc | TextField | Yes | NULL | User-friendly failure description |

**New Status**:
- `manual_make`: Payment succeeded but drink preparation requires manual intervention (customer likely left)

### Configuration Settings

**Location**: `coffee_payment/coffee_payment/settings.py`

**New Settings**:
```python
# Background payment check configuration
PAYMENT_CHECK_INTERVAL_S = 10  # How often to run the background task
FAST_TRACK_LIMIT_S = 300  # 5 minutes - threshold for fast vs slow track
FAST_TRACK_INTERVAL_S = 5  # Check every 5 seconds for fast track
SLOW_TRACK_INTERVAL_S = 60  # Check every 60 seconds for slow track
PAYMENT_ATTEMPTS_LIMIT = 10  # Maximum check attempts before marking as failed
PAYMENT_API_TIMEOUT_S = 3  # Timeout for payment provider API calls
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, several properties can be consolidated to reduce redundancy:

**Consolidations:**
1. Properties about timestamp updates (1.2, 1.3, 1.4, 3.4) can be combined into a single property about timezone-aware timestamp management
2. Properties about next_check_at being set to null (2.3, 7.3, 8.2, 9.2, 10.2) represent the same behavior across different status transitions - can be combined
3. Properties about fast track success handling (7.1, 7.2, 7.3) and slow track success handling (8.1, 8.2, 8.3) can be combined into comprehensive success handling properties
4. Properties about Yookassa scenarios (4.1, 4.2) can be combined since they have identical behavior
5. Properties about network error handling (5.1, 5.2, 5.3, 5.4, 5.5) can be combined into two properties: one for retry logic, one for failure after exhaustion

**Unique Properties Retained:**
- Order field initialization (1.1, 1.5)
- Manual make behavior (2.1, 2.2)
- Query filtering and sorting (3.1, 3.2)
- Check attempts increment (3.3)
- API integration patterns (4.3, 4.4)
- Pending status handling (6.1, 6.2, 6.3)
- Status-specific transitions (9.1, 10.1)
- Webhook consistency (11.1, 11.2, 11.3, 11.4)

### Correctness Properties

Property 1: Order initialization sets default values
*For any* newly created Order, the check_attempts field should be initialized to zero
**Validates: Requirements 1.1**

Property 2: Timezone-aware timestamp management
*For any* Order operation that sets payment_started_at, next_check_at, or last_check_at, the timestamp should include timezone information
**Validates: Requirements 1.2, 1.3, 1.4, 3.4**

Property 3: Failed orders store user-friendly descriptions
*For any* Order that transitions to failed status, the failed_presentation_desc field should be populated with a non-empty user-friendly message
**Validates: Requirements 1.5**

Property 4: Delayed payment success triggers manual make
*For any* Order where payment succeeds and (current_time - payment_started_at) > FAST_TRACK_LIMIT_S, the Order status should transition to manual_make
**Validates: Requirements 2.1, 8.1**

Property 5: Manual make orders do not trigger drink preparation
*For any* Order in manual_make status, processing the order should not result in TMetr API make command calls
**Validates: Requirements 2.2, 8.3**

Property 6: Terminal status transitions clear next check
*For any* Order that transitions to manual_make, not_paid, failed, or paid status, the next_check_at field should be set to null
**Validates: Requirements 2.3, 7.3, 8.2, 9.2, 10.2**

Property 7: Background task queries correct pending orders
*For any* execution of the background task, the queried Orders should have status='pending' AND next_check_at <= current_time AND expires_at > current_time
**Validates: Requirements 3.1**

Property 8: Background task sorts by newest first
*For any* set of Orders retrieved by the background task, they should be ordered by payment_started_at in descending order (newest first)
**Validates: Requirements 3.2**

Property 9: Check attempts increment on each check
*For any* Order processed by the background task, the check_attempts value after processing should equal the value before processing plus one
**Validates: Requirements 3.3**

Property 10: Yookassa scenarios trigger API calls
*For any* Order with payment_scenario in ['Yookassa', 'YookassaReceipt'], processing should result in a GET request to Yookassa API with the Order's payment_reference_id
**Validates: Requirements 4.1, 4.2**

Property 11: Payment API calls respect timeout
*For any* payment provider API call, the request should timeout if not completed within PAYMENT_API_TIMEOUT_S seconds
**Validates: Requirements 4.3**

Property 12: Non-Yookassa scenarios skip payment checks
*For any* Order with payment_scenario not in ['Yookassa', 'YookassaReceipt'], processing should not result in payment provider API calls
**Validates: Requirements 4.4**

Property 13: Network errors trigger retry within limit
*For any* Order where payment check encounters network error AND check_attempts <= PAYMENT_ATTEMPTS_LIMIT, the Order status should remain unchanged AND next_check_at should be set to (current_time + FAST_TRACK_INTERVAL_S)
**Validates: Requirements 5.1, 5.2**

Property 14: Exhausted retries mark order as failed
*For any* Order where payment check encounters network error AND check_attempts > PAYMENT_ATTEMPTS_LIMIT, the Order status should transition to failed AND failed_presentation_desc should be populated AND next_check_at should be null
**Validates: Requirements 5.3, 5.4, 5.5**

Property 15: Pending status uses fast track within limit
*For any* Order where payment provider returns pending AND (current_time - payment_started_at) <= FAST_TRACK_LIMIT_S, the Order status should remain pending AND next_check_at should be set to (current_time + FAST_TRACK_INTERVAL_S)
**Validates: Requirements 6.1, 6.3**

Property 16: Pending status uses slow track beyond limit
*For any* Order where payment provider returns pending AND (current_time - payment_started_at) > FAST_TRACK_LIMIT_S, the Order status should remain pending AND next_check_at should be set to (current_time + SLOW_TRACK_INTERVAL_S)
**Validates: Requirements 6.2, 6.3**

Property 17: Fast track success triggers drink preparation
*For any* Order where payment provider returns succeeded AND (current_time - payment_started_at) <= FAST_TRACK_LIMIT_S, the Order status should transition to paid AND a TMetr API make command should be sent AND next_check_at should be null
**Validates: Requirements 7.1, 7.2, 7.3**

Property 18: Canceled payments mark order as not paid
*For any* Order where payment provider returns canceled, the Order status should transition to not_paid AND next_check_at should be null
**Validates: Requirements 9.1, 9.2**

Property 19: Waiting for capture marks order as failed
*For any* Order where payment provider returns waiting_for_capture, the Order status should transition to failed AND next_check_at should be null
**Validates: Requirements 10.1, 10.2**

Property 20: Webhook fast track success triggers drink preparation
*For any* Order processed by webhook where payment status is succeeded AND (current_time - payment_started_at) <= FAST_TRACK_LIMIT_S, a TMetr API make command should be sent
**Validates: Requirements 11.1**

Property 21: Webhook slow track success triggers manual make
*For any* Order processed by webhook where payment status is succeeded AND (current_time - payment_started_at) > FAST_TRACK_LIMIT_S, the Order status should transition to manual_make
**Validates: Requirements 11.2**

Property 22: Webhook canceled transitions to not paid
*For any* Order processed by webhook where payment status is canceled, the Order status should transition to not_paid
**Validates: Requirements 11.3**

Property 23: Webhook waiting for capture transitions to failed
*For any* Order processed by webhook where payment status is waiting_for_capture, the Order status should transition to failed
**Validates: Requirements 11.4**

## Error Handling

### Network Errors

**Strategy**: Graceful degradation with retry logic

**Implementation**:
1. Wrap all payment provider API calls in try-except blocks
2. Catch `requests.RequestException` and subclasses
3. Log error details with order context
4. Apply retry logic based on check_attempts
5. Set appropriate next_check_at for retry or mark as failed

**User Impact**: Orders continue to be checked until retry limit is reached

### API Timeout Errors

**Strategy**: Treat as network errors

**Implementation**:
1. Configure requests timeout to PAYMENT_API_TIMEOUT_S
2. Handle `requests.Timeout` exception
3. Apply same retry logic as network errors

**User Impact**: Prevents indefinite waiting on slow API responses

### Invalid Payment Status

**Strategy**: Log and skip

**Implementation**:
1. Validate payment status against known values
2. Log unexpected statuses with full response
3. Do not update order status
4. Schedule next check normally

**User Impact**: System continues checking until valid status is received

### Missing payment_reference_id

**Strategy**: Mark as failed immediately

**Implementation**:
1. Check for payment_reference_id before API call
2. If missing, transition to failed status
3. Set failed_presentation_desc to indicate configuration error

**User Impact**: Prevents repeated failed API calls

### Database Errors

**Strategy**: Let Celery retry mechanism handle

**Implementation**:
1. Do not catch database exceptions
2. Rely on Celery's automatic retry
3. Log errors for monitoring

**User Impact**: Transient database issues are automatically retried

## Testing Strategy

### Unit Testing

**Scope**: Individual components and functions

**Key Test Cases**:
1. PaymentStatusService.check_payment_status() with mocked API responses
2. PaymentStatusService.process_payment_status() with various timing scenarios
3. PaymentStatusService.handle_check_error() with different attempt counts
4. Order model field initialization
5. Order query filtering logic
6. Time calculation functions (fast/slow track determination)

**Mocking Strategy**:
- Mock Yookassa API calls using `unittest.mock`
- Mock TMetr API calls
- Mock Django timezone.now() for time-based tests
- Use in-memory SQLite database for model tests

### Integration Testing

**Scope**: End-to-end workflows

**Key Test Cases**:
1. Complete background check cycle for pending order
2. Fast track success flow (check → paid → TMetr command)
3. Slow track success flow (check → manual_make)
4. Retry logic with network errors
5. Failure after exhausting retries
6. Webhook processing with shared logic
7. Multiple orders processed in single task run

**Test Environment**:
- Use Django test database
- Mock external APIs (Yookassa, TMetr)
- Use Celery eager mode for synchronous task execution

### Property-Based Testing

**Framework**: Hypothesis (Python property-based testing library)

**Configuration**: Minimum 100 iterations per property test

**Property Test Implementation**:
Each correctness property will be implemented as a property-based test using Hypothesis to generate random test data:

1. **Property 1-3**: Generate random Orders with various field values
2. **Property 4-6**: Generate Orders with random payment_started_at timestamps
3. **Property 7-9**: Generate sets of Orders with random field combinations
4. **Property 10-12**: Generate Orders with random payment scenarios
5. **Property 13-14**: Generate Orders with random check_attempts values
6. **Property 15-16**: Generate Orders with random timing values
7. **Property 17-23**: Generate Orders with random payment statuses and timings

**Test Tagging**: Each property-based test will include a comment:
```python
# Feature: background-payment-check, Property N: <property description>
```

### Manual Testing

**Scope**: Real-world scenarios with actual payment providers (test environment)

**Test Cases**:
1. Create order and complete payment quickly (< 5 minutes)
2. Create order and complete payment slowly (> 5 minutes)
3. Create order and cancel payment
4. Create order and let it timeout
5. Verify webhook and background check both work
6. Verify manual_make orders appear in admin interface

## Implementation Notes

### Celery Setup

**Requirements**:
- Install Celery: `pip install celery`
- Install Redis as message broker: `pip install redis`
- Configure Celery in Django settings

**Minimal Configuration**:
```python
# settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'check-pending-payments': {
        'task': 'payments.tasks.check_pending_payments',
        'schedule': PAYMENT_CHECK_INTERVAL_S,
    },
}
```

### Database Migration

**Migration File**: `payments/migrations/000X_add_payment_check_fields.py`

**Operations**:
1. Add payment_started_at field
2. Add next_check_at field
3. Add last_check_at field
4. Add check_attempts field with default=0
5. Add failed_presentation_desc field
6. Add 'manual_make' to status choices

### Yookassa API Integration

**Endpoint**: `GET /v3/payments/{payment_id}`

**Authentication**: Basic auth with account_id and secret_key from MerchantCredentials

**Response Format**:
```json
{
  "id": "payment_id",
  "status": "pending|succeeded|canceled|waiting_for_capture",
  "amount": {...},
  "created_at": "...",
  ...
}
```

**Timeout**: 3 seconds

### Shared Logic Pattern

**Approach**: Extract common payment processing logic into PaymentStatusService

**Benefits**:
1. Single source of truth for payment status handling
2. Consistent behavior between webhook and background check
3. Easier to test and maintain
4. Reduces code duplication

**Implementation**:
```python
# In webhook handler
def yookassa_payment_result_webhook(request):
    # ... existing webhook parsing ...
    
    # Use shared service
    PaymentStatusService.process_payment_status(order, payment_status)
    
    # ... existing response ...

# In background task
def check_pending_payments():
    orders = get_pending_orders()
    for order in orders:
        result = PaymentStatusService.check_payment_status(order)
        if result['error']:
            PaymentStatusService.handle_check_error(order, result['error'])
        else:
            PaymentStatusService.process_payment_status(order, result['status'])
```

### Logging Strategy

**Log Levels**:
- INFO: Normal operations (task start, orders found, status updates)
- WARNING: Retryable errors (network issues, timeouts)
- ERROR: Non-retryable errors (missing payment_reference_id, exhausted retries)

**Log Format**: JSON with structured fields
```json
{
  "timestamp": "2025-11-23T10:30:00+03:00",
  "level": "INFO",
  "task": "check_pending_payments",
  "order_id": "order-uuid",
  "message": "Payment status checked",
  "payment_status": "succeeded",
  "check_attempts": 3,
  "time_since_payment_started": 120
}
```

### Performance Considerations

**Database Queries**:
- Use select_related() to fetch Device and Merchant in single query
- Add database index on (status, next_check_at, expires_at) for efficient filtering
- Limit query results if needed (e.g., max 100 orders per task run)

**API Rate Limiting**:
- Process orders sequentially to avoid overwhelming payment provider APIs
- Consider adding delay between API calls if rate limits are hit
- Log API response times for monitoring

**Celery Worker Scaling**:
- Start with single worker for MVP
- Monitor task execution time
- Scale workers if task queue grows

### Deployment Considerations

**New Services**:
1. Celery worker process
2. Celery beat scheduler process
3. Redis server (if not already running)

**Process Management**:
- Use systemd or supervisor to manage Celery processes
- Ensure processes restart on failure
- Monitor process health

**Configuration**:
- Add new settings to environment variables
- Update deployment documentation
- Add health check endpoints for Celery

### Backward Compatibility

**Existing Orders**:
- Orders created before this feature will have NULL values for new fields
- Background task will skip orders without payment_started_at
- Webhook will continue to work for old orders

**Gradual Rollout**:
1. Deploy database migration
2. Deploy code changes
3. Start Celery worker and beat
4. Monitor logs for errors
5. Verify orders are being processed

## Future Enhancements

1. **Admin Interface**: Add Django admin actions to manually trigger checks or reset failed orders
2. **Metrics Dashboard**: Track check success rates, average check times, failure reasons
3. **Configurable Intervals**: Allow per-merchant configuration of check intervals
4. **Webhook Fallback Detection**: Detect when webhooks are consistently failing and increase check frequency
5. **Payment Provider Abstraction**: Extend to support TBank and other providers
6. **Notification System**: Alert operators when orders enter manual_make status
7. **Automatic Retry**: Implement exponential backoff for network errors
8. **Circuit Breaker**: Temporarily disable checks if payment provider API is down
