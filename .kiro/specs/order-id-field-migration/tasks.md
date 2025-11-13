# Implementation Plan

- [x] 1. Update Order model to use CharField primary key
  - Modify Order model in `coffee_payment/payments/models.py` to change id field from UUIDField to CharField(max_length=255)
  - Rename external_order_id field to payment_reference_id
  - Remove uuid.uuid4 default from id field
  - Update model docstrings to reflect machine-generated ID usage
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Create database migration for Order model changes
  - Create Django migration file for Order model schema changes
  - Implement forward migration with temporary field strategy to preserve existing UUID data
  - Add data migration function to copy UUID values to temporary CharField
  - Implement field swap logic (remove old id, rename temp to id)
  - Implement reverse migration for rollback capability
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 3. Update validation service for string-based order IDs
  - Modify `check_order_existence()` in `validation_service.py` to work with string IDs
  - Update `execute_validation_chain()` parameter naming from order_uuid to order_id
  - Update logging statements to reflect string-based ID format
  - Remove any UUID parsing or conversion logic
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Update views to use machine-generated order IDs
  - Modify `process_payment_flow()` in `views.py` to use machine-generated ID from QR parameters
  - Update order creation logic to set id=order_uuid directly
  - Add validation for empty or invalid order IDs
  - Update `yookassa_payment_result_webhook()` to lookup orders by id instead of external_order_id
  - Update webhook to store payment system ID in payment_reference_id field
  - Update `initiate_payment()` to work with string-based order IDs
  - _Requirements: 1.1, 4.1, 4.2_

- [x] 5. Add error handling for invalid order IDs
  - Add 'invalid_order_id' message to `user_messages.py`
  - Add try-except block in `process_payment_flow()` to catch IntegrityError for invalid IDs
  - Add validation for order ID length (max 255 characters)
  - Add validation for non-empty order ID
  - Update error logging to include order ID format information
  - _Requirements: 1.4, 4.1_

- [x] 6. Update payment services for string-based order references
  - Review `yookassa_service.py` payment metadata to ensure order.id is properly converted to string
  - Review `t_bank_service.py` for any order ID references
  - Update any UUID-specific logic to work with string IDs
  - Verify payment webhook processing uses order ID from metadata correctly
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 7. Create unit tests for Order model with machine-generated IDs
  - Write test for order creation with machine-generated ID format
  - Write test for order creation with 255-character ID (boundary condition)
  - Write test for order creation with invalid/empty ID (expect IntegrityError)
  - Write test for order lookup by machine-generated ID
  - Write test for ForeignKey relationships with string-based primary key
  - _Requirements: 5.1_

- [ ]* 8. Create integration tests for payment flow with machine IDs
  - Write test for complete payment flow from QR scan to webhook with machine ID
  - Write test for duplicate order handling with machine-generated ID
  - Write test for expired order validation with machine ID
  - Write test for webhook order lookup using machine-generated ID
  - _Requirements: 5.2_

- [ ]* 9. Create migration tests
  - Write test for UUID to string conversion during migration
  - Write test for ForeignKey relationship preservation during migration
  - Write test for migration rollback functionality
  - _Requirements: 5.4_

- [x] 10. Run database migration and verify data integrity
  - Create database backup before migration
  - Run migration on development environment
  - Verify all existing orders migrated successfully
  - Verify ForeignKey relationships intact
  - Test order creation with machine-generated ID
  - Test order lookup and payment flow
  - _Requirements: 2.1, 2.2, 2.3, 2.4_
