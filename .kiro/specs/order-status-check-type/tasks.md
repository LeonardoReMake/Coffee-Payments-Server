# Implementation Plan

- [x] 1. Extend MerchantCredentials model with status_check_type field
  - Add status_check_type CharField with choices ('polling', 'webhook', 'none')
  - Set default value to 'polling'
  - Add help text explaining the field
  - Add validation for allowed values
  - _Requirements: 1.1, 1.2, 1.4_

- [ ]* 1.1 Write property test for MerchantCredentials status_check_type validation
  - **Property 1: Valid status check type values in MerchantCredentials**
  - **Validates: Requirements 1.1, 1.4**

- [ ]* 1.2 Write property test for MerchantCredentials default value
  - **Property 2: Default value for MerchantCredentials**
  - **Validates: Requirements 1.2**

- [ ]* 1.3 Write property test for MerchantCredentials field presence
  - **Property 3: Status check type field presence in MerchantCredentials**
  - **Validates: Requirements 1.3**

- [x] 2. Extend Order model with status_check_type field
  - Add status_check_type CharField with choices ('polling', 'webhook', 'none')
  - Make field nullable (null=True, blank=True)
  - Add help text explaining the field is fixed at creation time
  - _Requirements: 2.2, 2.4_

- [ ]* 2.1 Write property test for Order status_check_type field presence
  - **Property 6: Status check type field presence in Order**
  - **Validates: Requirements 2.4**

- [x] 3. Create database migration
  - Add status_check_type field to MerchantCredentials (default='polling')
  - Add status_check_type field to Order (nullable)
  - Backfill existing MerchantCredentials with 'polling'
  - Backfill existing Orders with 'polling'
  - Add database index on Order (status, status_check_type, next_check_at)
  - _Requirements: 1.1, 1.2, 2.2_

- [x] 4. Update payment initiation logic in views.py
  - In initiate_payment function, retrieve MerchantCredentials for payment scenario
  - Extract status_check_type from credentials
  - Set Order.status_check_type to the retrieved value
  - Add fallback to 'polling' if credentials not found
  - Add logging for status_check_type assignment
  - _Requirements: 2.1, 2.3_

- [ ]* 4.1 Write property test for status_check_type propagation
  - **Property 4: Status check type propagation to Order**
  - **Validates: Requirements 2.1**

- [ ]* 4.2 Write property test for status_check_type immutability
  - **Property 5: Status check type immutability in Order**
  - **Validates: Requirements 2.2, 2.3**

- [x] 5. Update Celery background task filtering
  - In check_pending_payments task, add status_check_type='polling' filter to Order query
  - Verify filter is combined with existing filters (status, next_check_at, expires_at)
  - Add logging to show number of orders filtered by status_check_type
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ]* 5.1 Write property test for Celery task filtering
  - **Property 7: Celery task filters only polling orders**
  - **Validates: Requirements 3.1, 3.2, 3.3**

- [ ]* 5.2 Write property test for existing filters preservation
  - **Property 8: Celery task preserves existing filters**
  - **Validates: Requirements 3.4**

- [x] 6. Update Django admin interface
  - Add status_check_type field to MerchantCredentials admin form
  - Add status_check_type field to Order admin (read-only)
  - Add help text for both fields
  - _Requirements: 1.1, 2.4_

- [x] 7. Write integration tests
  - Test full payment flow with different status_check_type values
  - Test Celery task execution with mixed order types
  - Test MerchantCredentials creation and update
  - Test Order creation with status_check_type propagation
  - Test migration correctness
  - _Requirements: 1.1, 2.1, 3.1_

- [x] 8. Update PROJECT.md documentation
  - Add new section "Order Status Check Type Configuration"
  - Explain three status_check_type values (polling, webhook, none)
  - Describe how to configure in MerchantCredentials
  - Explain impact on background payment checking
  - Provide guidance on when to use each type
  - Follow CONSTITUTION.md principles (MVP, minimalism)
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
