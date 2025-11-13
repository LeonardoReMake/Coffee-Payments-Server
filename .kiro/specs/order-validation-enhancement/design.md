# Design Document

## Overview

This design document describes the implementation of enhanced order validation for the coffee payment system. The feature adds a validation chain that executes before payment scenario processing, ensuring request integrity, order state consistency, and device availability. The design follows MVP principles with minimal abstractions while maintaining code quality and user experience standards.

## Architecture

### High-Level Flow

```
QR Code Scan → process_payment_flow()
                    ↓
            Validation Chain
                    ↓
        ┌───────────────────────┐
        │ 1. Hash Validation    │ (placeholder)
        └───────────────────────┘
                    ↓
        ┌───────────────────────┐
        │ 2. Order Existence    │
        │    Check              │
        └───────────────────────┘
                    ↓
        ┌───────────────────────┐
        │ 3. Device Status      │
        │    Check (Heartbeat)  │
        └───────────────────────┘
                    ↓
        [All validations pass]
                    ↓
        Continue to Payment Scenario
```

### Integration Points

The validation chain integrates into the existing `process_payment_flow()` function in `views.py`. Validations execute after parameter validation but before order creation and payment scenario routing.

**Current Flow:**
1. Extract request parameters
2. Validate required parameters
3. Validate device and merchant
4. Get drink information from Tmetr API
5. Create order
6. Route to payment scenario

**Enhanced Flow:**
1. Extract request parameters
2. Validate required parameters
3. **[NEW] Execute validation chain**
4. Validate device and merchant
5. Get drink information from Tmetr API
6. Create order (conditional on validation results)
7. Route to payment scenario

## Components and Interfaces

### 1. Validation Service (`validation_service.py`)

A new service module that encapsulates all validation logic.

**Location:** `coffee_payment/payments/services/validation_service.py`

**Class:** `OrderValidationService`

**Methods:**

```python
class OrderValidationService:
    """
    Service for validating orders before payment processing.
    Executes validation chain with early termination on failure.
    """
    
    @staticmethod
    def validate_request_hash(request_params: dict) -> tuple[bool, str]:
        """
        Validates request hash for authenticity.
        
        Args:
            request_params: Dictionary containing all request parameters
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passes, False otherwise
            - error_message: Error message key from user_messages.py if validation fails
        """
        pass  # Placeholder implementation
    
    @staticmethod
    def check_order_existence(order_uuid: str) -> tuple[bool, str, Order | None]:
        """
        Checks if order exists and validates its state.
        
        Args:
            order_uuid: UUID of the order to check
            
        Returns:
            Tuple of (should_create_new, error_message, existing_order)
            - should_create_new: True if new order should be created
            - error_message: Error message key if order is invalid
            - existing_order: Order instance if exists and valid, None otherwise
        """
        pass
    
    @staticmethod
    def check_device_online_status(device_uuid: str) -> tuple[bool, str]:
        """
        Checks if device is online by querying Tmetr heartbeat API.
        
        Args:
            device_uuid: UUID of the device to check
            
        Returns:
            Tuple of (is_online, error_message)
            - is_online: True if device is online, False otherwise
            - error_message: Error message key if device is offline or check fails
        """
        pass
    
    @staticmethod
    def execute_validation_chain(request_params: dict, device_uuid: str, order_uuid: str) -> dict:
        """
        Executes complete validation chain with early termination.
        
        Args:
            request_params: All request parameters for hash validation
            device_uuid: UUID of the device
            order_uuid: UUID of the order
            
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'error_message': str | None,
                'existing_order': Order | None,
                'should_create_new_order': bool
            }
        """
        pass
```

### 2. Tmetr Service Extension

Extend existing `TmetrService` class with heartbeat functionality.

**Location:** `coffee_payment/payments/services/tmetr_service.py`

**New Method:**

```python
def get_device_heartbeat(self, device_id: str) -> Dict[str, Any]:
    """
    Get last heartbeat for a device from Tmetr API.
    
    Args:
        device_id: UUID of the device
        
    Returns:
        API response containing heartbeat data:
        {
            'content': [
                {
                    'deviceId': str,
                    'deviceIotName': str,
                    'heartbeatCreatedAt': int  # Unix timestamp in server timezone
                }
            ],
            'totalElements': int,
            'offset': int,
            'limit': int
        }
        
    Raises:
        requests.RequestException: If API request fails
    """
    pass
```

### 3. User Messages Extension

Add new error messages to `user_messages.py`.

**Location:** `coffee_payment/payments/user_messages.py`

**New Messages:**

```python
ERROR_MESSAGES = {
    # ... existing messages ...
    'invalid_request_hash': 'Некорректный запрос. Пожалуйста, отсканируйте QR-код снова.',
    'device_offline': 'Кофемашина недоступна. Пожалуйста, попробуйте другое устройство или обратитесь к администратору.',
    'heartbeat_check_failed': 'Не удалось проверить статус устройства. Пожалуйста, попробуйте позже.',
}
```

### 4. Settings Configuration

Add new configuration parameter for device online threshold.

**Location:** `coffee_payment/coffee_payment/settings.py`

**New Setting:**

```python
# Device online threshold in minutes
# If last heartbeat is older than this value, device is considered offline
DEVICE_ONLINE_THRESHOLD_MINUTES = 5
```

### 5. Views Integration

Modify `process_payment_flow()` to integrate validation chain.

**Location:** `coffee_payment/payments/views.py`

**Integration Point:** After parameter validation, before device/merchant validation

**Pseudocode:**

```python
def process_payment_flow(request):
    # ... existing parameter extraction and validation ...
    
    # Execute validation chain
    validation_result = OrderValidationService.execute_validation_chain(
        request_params={...},
        device_uuid=device_uuid,
        order_uuid=order_uuid
    )
    
    if not validation_result['valid']:
        return render_error_page(validation_result['error_message'], 400)
    
    # ... continue with existing flow ...
    
    # Conditional order creation
    if validation_result['should_create_new_order']:
        order = Order.objects.create(...)
    else:
        order = validation_result['existing_order']
    
    # ... continue to payment scenario ...
```

## Data Models

No new models required. The feature uses existing models:

- **Order**: Used for order existence check and expiration validation
- **Device**: Used for device UUID validation (existing functionality)

## Error Handling

### Validation Chain Error Handling

Each validation step returns a tuple indicating success/failure and error message. The validation chain:

1. Executes validations sequentially
2. Stops on first failure
3. Returns error message key from `user_messages.py`
4. Logs all validation attempts with full context

### API Error Handling

**Tmetr Heartbeat API Errors:**

- **Network errors**: Log error, return device offline status
- **API errors (4xx/5xx)**: Log error, return heartbeat check failed status
- **Timeout**: Log error, return heartbeat check failed status
- **Invalid response format**: Log error, return heartbeat check failed status

### User Experience

All errors display through the existing `render_error_page()` function with:

- User-friendly message from `user_messages.py`
- Appropriate HTTP status code (400 for validation failures)
- Mobile-first responsive design
- No technical details exposed to users

## Testing Strategy

### Unit Tests

**Test File:** `coffee_payment/tests/test_order_validation.py`

**Test Cases:**

1. **Hash Validation Tests**
   - Test placeholder implementation returns success
   - Test logging of hash validation attempts

2. **Order Existence Tests**
   - Test non-existent order returns should_create_new=True
   - Test existing order with status 'created' and not expired returns existing order
   - Test existing order with expired expires_at returns error
   - Test existing order with other statuses

3. **Device Status Tests**
   - Test device online when heartbeat within threshold
   - Test device offline when heartbeat exceeds threshold
   - Test Tmetr API error handling
   - Test missing heartbeat data handling
   - Test timezone handling in heartbeat comparison

4. **Validation Chain Tests**
   - Test early termination on hash validation failure
   - Test early termination on order validation failure
   - Test early termination on device status failure
   - Test successful validation chain execution
   - Test logging at each step

### Integration Tests

**Test File:** `coffee_payment/tests/test_order_validation_integration.py`

**Test Cases:**

1. Test complete flow with all validations passing
2. Test flow termination on hash validation failure
3. Test flow with existing valid order (no new order created)
4. Test flow with expired order
5. Test flow with offline device
6. Test error page rendering for each validation failure

### Test Configuration

- All tests run with 30-second timeout
- Use Django test database
- Mock Tmetr API calls for predictable testing
- Verify conda environment activation before test execution

## Implementation Notes

### MVP Principles

1. **Hash validation placeholder**: Implement as pass-through that always succeeds, allowing future implementation without changing interface
2. **Simple validation chain**: Sequential execution with early termination, no complex state machines
3. **Reuse existing components**: Leverage existing `TmetrService`, `render_error_page()`, logging utilities
4. **Minimal configuration**: Single threshold setting for device online status

### Logging Requirements

All log entries must include:

- Timestamp with timezone
- Function name
- All relevant parameters
- Validation result (pass/fail)
- Error details for failures

**Example Log Entries:**

```
[2025-11-13T10:30:00+03:00] INFO [execute_validation_chain] Starting validation chain. device_uuid=abc-123, order_uuid=xyz-789
[2025-11-13T10:30:00+03:00] INFO [validate_request_hash] Hash validation passed (placeholder)
[2025-11-13T10:30:00+03:00] INFO [check_order_existence] Order xyz-789 not found, will create new order
[2025-11-13T10:30:01+03:00] INFO [check_device_online_status] Checking device abc-123 heartbeat. API params: deviceIds=['abc-123'], offset=0, limit=1
[2025-11-13T10:30:01+03:00] INFO [check_device_online_status] Device abc-123 is online. Last heartbeat: 2025-11-13T10:28:00+03:00, threshold: 5 minutes
[2025-11-13T10:30:01+03:00] INFO [execute_validation_chain] Validation chain completed successfully
```

### Timezone Handling

- Use Django's timezone-aware datetime objects
- Store server timezone offset in settings
- Include timezone offset in Tmetr API requests via `X-TimeZoneOffset` header
- Convert heartbeat timestamps considering timezone offset
- Log all timestamps with explicit timezone information

### Performance Considerations

- Validation chain adds ~1-2 seconds to request processing (Tmetr API call)
- Consider caching device heartbeat status for 30 seconds to reduce API calls (future optimization)
- Current implementation prioritizes correctness over performance (MVP principle)

## Deployment Considerations

### Configuration Changes

1. Add `DEVICE_ONLINE_THRESHOLD_MINUTES` to settings
2. Verify Tmetr API credentials have heartbeat endpoint access
3. Update environment variables if needed

### Database Migrations

No database migrations required.

### Backward Compatibility

- Existing QR codes continue to work
- Existing orders unaffected
- New validation adds safety without breaking existing functionality

### Monitoring

Add monitoring for:

- Validation chain failure rates
- Device offline detection frequency
- Tmetr heartbeat API response times
- Order expiration rates

## Future Enhancements

1. **Hash validation implementation**: Complete the placeholder with actual hash verification logic
2. **Heartbeat caching**: Cache device online status to reduce API calls
3. **Configurable validation chain**: Allow enabling/disabling specific validations via settings
4. **Validation metrics**: Track validation performance and failure patterns
5. **Retry logic**: Add retry mechanism for transient Tmetr API failures
