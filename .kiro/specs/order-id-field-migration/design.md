# Design Document

## Overview

This design document outlines the migration of the Order model's primary key from Django's UUIDField to CharField to support machine-generated order IDs. Coffee machines generate order IDs in custom formats (e.g., `20250317110122659ba6d7-9ace-cndn`) that don't conform to RFC 4122 UUID standards. The migration must preserve all existing data, maintain referential integrity, and ensure backward compatibility with the existing codebase.

## Architecture

### Current State

The Order model currently uses:
- `id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`
- `external_order_id = models.CharField(max_length=255, null=True, blank=True)` for payment system references

Related models (Payment, Receipt, TBankPayment) reference Order via ForeignKey relationships.

### Target State

The Order model will use:
- `id = models.CharField(primary_key=True, max_length=255)` for machine-generated IDs
- Remove `external_order_id` field (no longer needed as payment IDs will be stored separately if needed)
- All ForeignKey relationships remain intact with automatic Django handling

### Migration Strategy

**Two-phase migration approach:**

1. **Phase 1: Schema Migration**
   - Convert Order.id from UUIDField to CharField(max_length=255)
   - Preserve all existing UUID values as strings
   - Django automatically handles ForeignKey updates in related tables

2. **Phase 2: Code Updates**
   - Update Order creation logic to use machine-generated IDs from QR parameters
   - Remove uuid.uuid4 default generation
   - Update validation service to work with string IDs
   - Update all Order queries to use string-based lookups

## Components and Interfaces

### 1. Order Model Changes

**File:** `coffee_payment/payments/models.py`

**Changes:**
```python
class Order(models.Model):
    # OLD: id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # NEW:
    id = models.CharField(primary_key=True, max_length=255)
    
    # Remove external_order_id field (no longer needed)
    # OLD: external_order_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Add new field for payment system references
    payment_reference_id = models.CharField(max_length=255, null=True, blank=True, 
                                           help_text='Payment system reference ID (e.g., Yookassa payment_id)')
    
    # ... rest of fields remain unchanged
```

**Rationale:**
- CharField(max_length=255) accommodates machine-generated IDs of varying formats
- Removing external_order_id simplifies the model (machine ID becomes the primary identifier)
- Adding payment_reference_id maintains payment system tracking capability

### 2. Database Migration

**File:** `coffee_payment/payments/migrations/00XX_migrate_order_id_to_charfield.py`

**Migration Operations:**

```python
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('payments', '00XX_previous_migration'),
    ]

    operations = [
        # Step 1: Add temporary CharField field
        migrations.AddField(
            model_name='order',
            name='id_temp',
            field=models.CharField(max_length=255, null=True),
        ),
        
        # Step 2: Copy UUID values to temporary field as strings
        migrations.RunPython(copy_uuid_to_temp_field),
        
        # Step 3: Remove old UUID primary key
        migrations.RemoveField(
            model_name='order',
            name='id',
        ),
        
        # Step 4: Rename temporary field to id and make it primary key
        migrations.RenameField(
            model_name='order',
            old_name='id_temp',
            new_name='id',
        ),
        
        migrations.AlterField(
            model_name='order',
            name='id',
            field=models.CharField(primary_key=True, max_length=255),
        ),
        
        # Step 5: Rename external_order_id to payment_reference_id
        migrations.RenameField(
            model_name='order',
            old_name='external_order_id',
            new_name='payment_reference_id',
        ),
    ]

def copy_uuid_to_temp_field(apps, schema_editor):
    Order = apps.get_model('payments', 'Order')
    for order in Order.objects.all():
        order.id_temp = str(order.id)
        order.save(update_fields=['id_temp'])
```

**Migration Safety:**
- Uses temporary field to avoid data loss
- Converts UUIDs to strings preserving all existing references
- Django automatically updates ForeignKey relationships
- Reversible migration for rollback capability

### 3. Views Layer Updates

**File:** `coffee_payment/payments/views.py`

**Changes in `process_payment_flow()`:**

```python
# Extract order UUID from QR code parameters
order_uuid = request.GET.get('uuid')  # This is now machine-generated ID

# ... validation chain execution ...

# Order creation with machine-generated ID
if validation_result['should_create_new_order']:
    order = Order.objects.create(
        id=order_uuid,  # Use machine-generated ID directly
        drink_name=drink_name,
        device=device,
        merchant=merchant,
        size=drink_size_int,
        price=drink_price,
        status='created'
    )
```

**Changes in `yookassa_payment_result_webhook()`:**

```python
# OLD: order = Order.objects.get(external_order_id=payment_id)
# NEW: Store payment_id in payment_reference_id, lookup by order metadata

# Extract order_uuid from payment metadata
order_uuid = event_json['object']['metadata']['order_uuid']

# Find order by primary key (machine-generated ID)
order = Order.objects.get(id=order_uuid)

# Store payment system reference
order.payment_reference_id = payment_id
order.save(update_fields=['payment_reference_id'])
```

**Rationale:**
- Machine-generated ID from QR code becomes the authoritative order identifier
- Payment system IDs stored in payment_reference_id for tracking
- Webhook lookups use order_uuid from payment metadata (already present)

### 4. Validation Service Updates

**File:** `coffee_payment/payments/services/validation_service.py`

**Changes in `check_order_existence()`:**

```python
@staticmethod
def check_order_existence(order_id: str) -> Tuple[bool, Optional[str], Optional[Order]]:
    """
    Checks if order exists and validates its state.
    
    Args:
        order_id: Machine-generated order ID (string format)
        
    Returns:
        Tuple of (should_create_new, error_message, existing_order)
    """
    logger.info(f"[check_order_existence] Checking order existence. order_id={order_id}")
    
    try:
        # Query by string ID (no UUID conversion needed)
        order = Order.objects.get(id=order_id)
        
        # ... rest of validation logic remains unchanged ...
```

**Changes in `execute_validation_chain()`:**

```python
@staticmethod
def execute_validation_chain(
    request_params: dict,
    device_uuid: str,
    order_id: str  # Renamed from order_uuid for clarity
) -> Dict[str, Any]:
    """
    Executes complete validation chain with early termination.
    
    Args:
        request_params: All request parameters for hash validation
        device_uuid: UUID of the device
        order_id: Machine-generated order ID (string format)
    """
    logger.info(
        f"[execute_validation_chain] Starting validation chain. "
        f"device_uuid={device_uuid}, order_id={order_id}"
    )
    
    # ... validation logic remains unchanged, just parameter name update ...
```

**Rationale:**
- No UUID parsing/conversion needed
- String-based lookups work directly with CharField primary key
- Validation logic remains unchanged (only parameter naming for clarity)

### 5. Payment Service Updates

**File:** `coffee_payment/payments/services/yookassa_service.py`

**Changes in payment metadata:**

```python
def create_payment(order, device, drink_details):
    """Create Yookassa payment with order metadata."""
    
    # ... existing code ...
    
    # Metadata includes order ID (now machine-generated format)
    metadata = {
        'order_uuid': str(order.id),  # Machine-generated ID
        'drink_number': drink_details.get('drink_id'),
        'size': str(order.size - 1),  # Convert back to 0-2 format
    }
    
    # ... rest of payment creation ...
```

**Rationale:**
- Metadata already uses order.id, no changes needed to logic
- String conversion ensures compatibility with payment system APIs
- Webhook can retrieve order using metadata['order_uuid']

## Data Models

### Order Model Schema

**Before Migration:**
```python
id: UUIDField (primary key, auto-generated)
external_order_id: CharField(255, nullable) - payment system reference
drink_name: CharField(255)
device: ForeignKey(Device)
merchant: ForeignKey(Merchant)
size: IntegerField
price: DecimalField
status: CharField(50)
expires_at: DateTimeField
created_at: DateTimeField
updated_at: DateTimeField
```

**After Migration:**
```python
id: CharField(255, primary key) - machine-generated ID
payment_reference_id: CharField(255, nullable) - payment system reference
drink_name: CharField(255)
device: ForeignKey(Device)
merchant: ForeignKey(Merchant)
size: IntegerField
price: DecimalField
status: CharField(50)
expires_at: DateTimeField
created_at: DateTimeField
updated_at: DateTimeField
```

### Related Models Impact

**Payment Model:**
- `order = ForeignKey(Order)` - Django automatically handles CharField primary key
- No code changes needed

**Receipt Model:**
- `order = ForeignKey(Order)` - Django automatically handles CharField primary key
- No code changes needed

**TBankPayment Model:**
- `order_id = CharField(255)` - Already uses CharField, no changes needed
- May need to update queries if they reference Order.id

## Error Handling

### Migration Errors

**Scenario:** Migration fails during UUID to string conversion

**Handling:**
- Migration is wrapped in transaction (Django default)
- Automatic rollback on failure
- Manual rollback available via `python manage.py migrate payments <previous_migration>`

**Logging:**
```python
logger.error(f"Migration failed at step X: {error_message}")
```

### Runtime Errors

**Scenario:** Invalid or empty order ID from QR code

**Handling:**
```python
# In process_payment_flow()
if not order_uuid or not order_uuid.strip():
    log_error('Invalid order ID in QR code parameters', 'process_payment_flow', 'ERROR')
    return render_error_page(ERROR_MESSAGES['invalid_order_id'], 400)
```

**New Error Message:**
```python
# In user_messages.py
ERROR_MESSAGES = {
    # ... existing messages ...
    'invalid_order_id': 'Некорректный идентификатор заказа. Пожалуйста, отсканируйте QR-код снова.',
}
```

**Scenario:** Order ID exceeds 255 characters

**Handling:**
- Database constraint will reject the insert
- Catch IntegrityError and return user-friendly message

```python
from django.db import IntegrityError

try:
    order = Order.objects.create(id=order_uuid, ...)
except IntegrityError as e:
    log_error(f'Order ID too long or invalid: {order_uuid}', 'process_payment_flow', 'ERROR')
    return render_error_page(ERROR_MESSAGES['invalid_order_id'], 400)
```

**Scenario:** Duplicate order ID from coffee machine

**Handling:**
- Validation chain already handles this via `check_order_existence()`
- If order exists and is valid, reuse it
- If order exists but expired, show error
- No additional handling needed

## Testing Strategy

### Unit Tests

**File:** `coffee_payment/tests/test_order_model.py`

**Test Cases:**

1. **test_order_creation_with_machine_id**
   - Create order with machine-generated ID format
   - Verify ID is stored correctly
   - Verify all fields are populated

2. **test_order_creation_with_long_id**
   - Create order with 255-character ID
   - Verify successful creation
   - Test boundary condition

3. **test_order_creation_with_invalid_id**
   - Attempt to create order with empty ID
   - Verify IntegrityError is raised
   - Attempt to create order with >255 character ID
   - Verify IntegrityError is raised

4. **test_order_lookup_by_machine_id**
   - Create order with machine ID
   - Query by ID
   - Verify correct order is returned

5. **test_foreign_key_relationships**
   - Create order with machine ID
   - Create payment referencing order
   - Verify ForeignKey relationship works
   - Delete order and verify cascade behavior

### Integration Tests

**File:** `coffee_payment/tests/test_order_id_migration.py`

**Test Cases:**

1. **test_complete_payment_flow_with_machine_id**
   - Simulate QR code scan with machine-generated ID
   - Execute validation chain
   - Create order
   - Initiate payment
   - Process webhook
   - Verify order status updates correctly

2. **test_duplicate_order_handling**
   - Create order with machine ID
   - Attempt to create duplicate with same ID
   - Verify validation chain returns existing order
   - Verify no duplicate created

3. **test_expired_order_with_machine_id**
   - Create order with machine ID
   - Set expires_at to past time
   - Attempt to process payment
   - Verify error is returned

4. **test_webhook_order_lookup**
   - Create order with machine ID
   - Create payment with order_uuid in metadata
   - Simulate webhook callback
   - Verify order is found and updated correctly

### Migration Tests

**File:** `coffee_payment/tests/test_migration_00XX.py`

**Test Cases:**

1. **test_uuid_to_string_conversion**
   - Create orders with UUID IDs (pre-migration state)
   - Run migration
   - Verify all UUIDs converted to strings
   - Verify no data loss

2. **test_foreign_key_preservation**
   - Create orders with payments and receipts
   - Run migration
   - Verify all ForeignKey relationships intact
   - Verify related objects still accessible

3. **test_migration_rollback**
   - Run migration forward
   - Run migration backward
   - Verify database returns to original state
   - Verify data integrity maintained

### Test Execution

**Command:**
```bash
# Activate conda environment
conda activate base

# Run all tests with timeout
python manage.py test coffee_payment.tests --timeout=30

# Run specific test file
python manage.py test coffee_payment.tests.test_order_model --timeout=30
```

**Coverage Requirements:**
- Minimum 90% code coverage for modified files
- All error paths must be tested
- All validation scenarios must be tested

## Deployment Considerations

### Pre-Deployment Checklist

1. **Database Backup**
   - Create full database backup before migration
   - Test backup restoration procedure
   - Document rollback steps

2. **Migration Testing**
   - Test migration on staging environment with production data copy
   - Verify migration completes successfully
   - Verify application functionality post-migration
   - Measure migration duration for production planning

3. **Monitoring Setup**
   - Add logging for order creation with machine IDs
   - Monitor error rates during rollout
   - Set up alerts for IntegrityError spikes

### Deployment Steps

1. **Deploy Code**
   - Deploy updated code to production
   - Do not run migrations yet

2. **Run Migration**
   ```bash
   python manage.py migrate payments
   ```

3. **Verify Migration**
   - Check migration status: `python manage.py showmigrations`
   - Verify order count matches pre-migration count
   - Test order creation with machine ID
   - Test order lookup by ID

4. **Monitor Application**
   - Watch logs for errors
   - Monitor order creation success rate
   - Check payment webhook processing

### Rollback Plan

**If issues detected:**

1. **Rollback Migration**
   ```bash
   python manage.py migrate payments <previous_migration_number>
   ```

2. **Rollback Code**
   - Deploy previous code version
   - Verify application functionality

3. **Restore Database** (if migration rollback fails)
   - Stop application
   - Restore from backup
   - Restart application
   - Verify functionality

### Post-Deployment Validation

1. **Functional Testing**
   - Scan QR code with machine-generated ID
   - Complete payment flow
   - Verify order created with correct ID
   - Verify webhook updates order correctly

2. **Data Validation**
   - Query orders created post-migration
   - Verify ID format matches machine-generated format
   - Verify no UUID-format IDs created post-migration

3. **Performance Monitoring**
   - Monitor database query performance
   - Check for slow queries on Order table
   - Verify index usage on id field

## Security Considerations

### Input Validation

**Order ID Validation:**
- Maximum length: 255 characters (enforced by database)
- Non-empty string (enforced by application logic)
- No SQL injection risk (Django ORM parameterized queries)

**Recommendation:**
- Add regex validation for expected machine ID format if pattern is known
- Log suspicious ID formats for security monitoring

### Data Integrity

**Primary Key Uniqueness:**
- Database enforces uniqueness constraint
- Application handles IntegrityError gracefully
- Validation chain prevents duplicate order creation

**Referential Integrity:**
- ForeignKey relationships maintained by Django ORM
- Cascade delete behavior preserved
- No orphaned records possible

## Performance Considerations

### Database Indexing

**Primary Key Index:**
- CharField primary key automatically indexed by database
- String comparison slightly slower than UUID comparison
- Impact negligible for typical query volumes

**Query Performance:**
- `Order.objects.get(id=order_id)` - O(1) with index
- No performance degradation expected

### Migration Performance

**Estimated Duration:**
- Small dataset (<10,000 orders): <1 minute
- Medium dataset (10,000-100,000 orders): 1-5 minutes
- Large dataset (>100,000 orders): 5-15 minutes

**Optimization:**
- Migration runs in single transaction
- Bulk update operations used where possible
- Minimal downtime required

## Future Enhancements

### Potential Improvements

1. **Order ID Format Validation**
   - Add regex pattern validation for machine ID format
   - Reject malformed IDs early in request processing
   - Improve error messages for specific format violations

2. **Order ID Generation Service**
   - Create centralized service for order ID validation
   - Support multiple machine ID formats
   - Provide ID format documentation for coffee machine vendors

3. **Audit Trail**
   - Track order ID changes (if needed)
   - Log all order creation attempts with ID format
   - Monitor ID format distribution for anomaly detection

4. **Performance Optimization**
   - Add database index on payment_reference_id if frequently queried
   - Consider partitioning Order table by date if volume grows
   - Implement caching for frequently accessed orders
