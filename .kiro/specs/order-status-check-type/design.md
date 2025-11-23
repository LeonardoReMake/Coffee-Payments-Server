# Design Document

## Overview

Данная фича добавляет гибкую настройку способа проверки статуса платежей в системе. Система будет поддерживать три типа проверки: polling (фоновый опрос), webhook (уведомления от платежной системы) и none (без автоматической проверки). Это позволит оптимизировать работу с различными платежными системами и снизить нагрузку на фоновые задачи.

Ключевое архитектурное решение — фиксация типа проверки в заказе при его создании. Это обеспечивает стабильность обработки заказа независимо от изменений в настройках мерчанта.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Payment Flow                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Get MerchantCredentials for Payment Scenario            │
│     - Retrieve status_check_type from credentials           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Create Order                                             │
│     - Copy status_check_type from MerchantCredentials       │
│     - Store in Order.status_check_type field                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Background Payment Checking (Celery Task)                │
│     - Filter: status='pending' AND                           │
│               status_check_type='polling' AND                │
│               next_check_at <= now AND                       │
│               expires_at > now                               │
│     - Process only orders with polling enabled               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Configuration Phase**: Администратор настраивает `status_check_type` в MerchantCredentials для каждого платежного сценария
2. **Order Creation Phase**: При создании платежа система копирует `status_check_type` из MerchantCredentials в Order
3. **Background Check Phase**: Celery задача фильтрует заказы по `status_check_type='polling'` и обрабатывает только их

## Components and Interfaces

### 1. MerchantCredentials Model Extension

**Location**: `coffee_payment/payments/models.py`

**Changes**:
- Add `status_check_type` field to MerchantCredentials model
- Add validation for allowed values
- Set default value to 'polling'

**Interface**:
```python
class MerchantCredentials(models.Model):
    # ... existing fields ...
    status_check_type = models.CharField(
        max_length=20,
        choices=[
            ('polling', 'Polling'),
            ('webhook', 'Webhook'),
            ('none', 'None')
        ],
        default='polling',
        help_text='Type of payment status check: polling (background check), webhook (notification from payment provider), or none (no automatic check)'
    )
```

### 2. Order Model Extension

**Location**: `coffee_payment/payments/models.py`

**Changes**:
- Add `status_check_type` field to Order model
- Field is set during order creation and never modified

**Interface**:
```python
class Order(models.Model):
    # ... existing fields ...
    status_check_type = models.CharField(
        max_length=20,
        choices=[
            ('polling', 'Polling'),
            ('webhook', 'Webhook'),
            ('none', 'None')
        ],
        null=True,
        blank=True,
        help_text='Type of payment status check for this order (fixed at creation time)'
    )
```

### 3. Payment Initiation Logic

**Location**: `coffee_payment/payments/views.py` (in `initiate_payment` function)

**Changes**:
- When creating payment, retrieve `status_check_type` from MerchantCredentials
- Set `Order.status_check_type` to the retrieved value

**Logic**:
```python
# Get merchant credentials for payment scenario
credentials = merchant.credentials.filter(scenario=device.payment_scenario).first()

# Set status_check_type in order
order.status_check_type = credentials.status_check_type if credentials else 'polling'
order.save()
```

### 4. Celery Background Task Filter

**Location**: `coffee_payment/payments/tasks.py`

**Changes**:
- Add `status_check_type='polling'` filter to order query

**Updated Query**:
```python
orders = Order.objects.filter(
    status='pending',
    status_check_type='polling',  # NEW FILTER
    next_check_at__lte=now,
    next_check_at__isnull=False,
    expires_at__gt=now
).select_related('device', 'merchant').order_by('-payment_started_at')
```

## Data Models

### MerchantCredentials

```python
{
    'id': UUID,
    'merchant': ForeignKey(Merchant),
    'scenario': str,  # 'Yookassa', 'TBank', 'Custom'
    'credentials': dict,  # JSON credentials
    'status_check_type': str,  # 'polling', 'webhook', 'none'
    'created_at': datetime,
    'updated_at': datetime
}
```

**Validation Rules**:
- `status_check_type` must be one of: 'polling', 'webhook', 'none'
- Default value: 'polling'

### Order

```python
{
    'id': str,
    # ... existing fields ...
    'status_check_type': str,  # 'polling', 'webhook', 'none'
    # ... other fields ...
}
```

**Business Rules**:
- `status_check_type` is set once during order creation
- Value is copied from MerchantCredentials at payment initiation time
- Field is never modified after initial setting
- If MerchantCredentials not found, defaults to 'polling'

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Valid status check type values in MerchantCredentials

*For any* MerchantCredentials record, the status_check_type field should only contain one of the three allowed values: 'polling', 'webhook', or 'none'.

**Validates: Requirements 1.1, 1.4**

### Property 2: Default value for MerchantCredentials

*For any* newly created MerchantCredentials without an explicit status_check_type value, the field should be set to 'polling'.

**Validates: Requirements 1.2**

### Property 3: Status check type field presence in MerchantCredentials

*For any* MerchantCredentials record retrieved from the database, the status_check_type field should be present and not null.

**Validates: Requirements 1.3**

### Property 4: Status check type propagation to Order

*For any* Order created with a payment, if MerchantCredentials exist for the payment scenario, the Order's status_check_type should equal the MerchantCredentials' status_check_type.

**Validates: Requirements 2.1**

### Property 5: Status check type immutability in Order

*For any* Order with a set status_check_type, updating the associated MerchantCredentials' status_check_type should not change the Order's status_check_type value.

**Validates: Requirements 2.2, 2.3**

### Property 6: Status check type field presence in Order

*For any* Order record retrieved from the database that has been through payment initiation, the status_check_type field should be present.

**Validates: Requirements 2.4**

### Property 7: Celery task filters only polling orders

*For any* set of Orders selected by the Celery background task query, all Orders should have status_check_type='polling'.

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 8: Celery task preserves existing filters

*For any* set of Orders selected by the Celery background task query, all Orders should satisfy the existing filter conditions (status='pending', next_check_at <= now, next_check_at is not null, expires_at > now) in addition to status_check_type='polling'.

**Validates: Requirements 3.4**

## Error Handling

### Missing MerchantCredentials

**Scenario**: Order creation when MerchantCredentials don't exist for the payment scenario

**Handling**:
- Set `Order.status_check_type = 'polling'` (default fallback)
- Log warning message
- Continue with order creation

**Rationale**: Ensures backward compatibility with existing orders and prevents payment flow interruption.

### Invalid status_check_type Value

**Scenario**: Attempt to set status_check_type to invalid value

**Handling**:
- Django model validation will reject the value
- Return validation error to admin interface
- Do not save the record

**Rationale**: Maintains data integrity and prevents undefined behavior.

### Database Migration

**Scenario**: Existing Orders and MerchantCredentials without status_check_type field

**Handling**:
- Migration sets `status_check_type='polling'` for all existing records
- Ensures all records have valid values after migration
- No manual intervention required

**Rationale**: Maintains backward compatibility and ensures smooth deployment.

## Testing Strategy

### Unit Testing

Unit tests will verify:
- Model field validation (allowed values, defaults)
- Order creation logic (status_check_type propagation)
- Celery task filtering logic
- Edge cases (missing credentials, null values)

**Test Files**:
- `coffee_payment/tests/test_order_status_check_type.py` — unit tests for models and logic
- `coffee_payment/tests/test_order_status_check_type_integration.py` — integration tests for full flow

### Property-Based Testing

Property-based tests will use **Hypothesis** library (already in requirements.txt) to verify correctness properties across many random inputs.

**Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with property number and requirement reference

**Test Coverage**:
- Property 1: Immutability test
- Property 2: Valid values test
- Property 3: Filtering test
- Property 4: Propagation test
- Property 5: Default value test

### Integration Testing

Integration tests will verify:
- Full payment flow with different status_check_type values
- Celery task execution with mixed order types
- Admin interface for setting status_check_type
- Database migration correctness

### Manual Testing

Manual testing checklist:
1. Create MerchantCredentials with each status_check_type value
2. Create orders and verify status_check_type propagation
3. Run Celery task and verify only polling orders are processed
4. Update MerchantCredentials and verify existing orders unchanged
5. Test admin interface for setting status_check_type

## Migration Strategy

### Database Migration

**File**: `coffee_payment/payments/migrations/00XX_add_status_check_type.py`

**Operations**:
1. Add `status_check_type` field to MerchantCredentials (default='polling')
2. Add `status_check_type` field to Order (nullable, default=None)
3. Backfill existing MerchantCredentials with 'polling'
4. Backfill existing Orders with 'polling' (for consistency)

**Backward Compatibility**:
- All existing records get 'polling' value (current behavior)
- No breaking changes to existing functionality
- Celery task continues to work with existing orders

### Deployment Steps

1. Deploy code with new fields (nullable)
2. Run database migration
3. Verify migration success
4. Update documentation
5. Notify administrators about new configuration option

## Documentation Updates

### PROJECT.md Updates

Add new section: **Order Status Check Type Configuration**

**Content**:
- Explanation of three status_check_type values
- How to configure in MerchantCredentials
- Impact on background payment checking
- When to use each type

**Location**: After "Конфигурация сценариев оплаты" section

### Admin Interface

**Changes**:
- Add `status_check_type` field to MerchantCredentials admin form
- Add help text explaining each option
- Add `status_check_type` to Order admin (read-only)

## Performance Considerations

### Celery Task Performance

**Impact**: Adding `status_check_type='polling'` filter will reduce the number of orders processed by Celery task.

**Benefits**:
- Reduced database queries
- Faster task execution
- Lower CPU usage
- Better scalability

**Metrics to Monitor**:
- Number of orders processed per task run
- Task execution time
- Database query count

### Database Indexing

**Recommendation**: Add database index on `Order.status_check_type` for faster filtering.

**Index**:
```python
class Order(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'status_check_type', 'next_check_at']),
        ]
```

**Rationale**: Celery task filters by multiple fields, composite index will improve query performance.

## Future Enhancements

1. **Dynamic Status Check Type**: Allow changing status_check_type for pending orders (with careful state management)
2. **Per-Device Configuration**: Override status_check_type at Device level
3. **Monitoring Dashboard**: Show distribution of orders by status_check_type
4. **Webhook Endpoint**: Implement webhook receiver for 'webhook' type orders
5. **Retry Logic**: Different retry strategies for different status_check_type values
