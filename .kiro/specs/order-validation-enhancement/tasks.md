# Implementation Plan

- [x] 1. Add configuration and user messages
  - Add `DEVICE_ONLINE_THRESHOLD_MINUTES` setting to `coffee_payment/coffee_payment/settings.py`
  - Add new error messages to `coffee_payment/payments/user_messages.py` for hash validation, device offline, and heartbeat check failures
  - _Requirements: 5.1, 5.2, 6.1, 6.2, 6.3_

- [x] 2. Extend TmetrService with heartbeat functionality
  - Add `get_device_heartbeat()` method to `TmetrService` class in `coffee_payment/payments/services/tmetr_service.py`
  - Implement POST request to `/api/ui/v1/stat/heartbeat/recent` endpoint
  - Include `X-TimeZoneOffset` header in request
  - Handle API response parsing and error cases
  - _Requirements: 3.1, 3.2, 3.7_

- [x] 3. Create OrderValidationService with validation methods
- [x] 3.1 Create validation service file and class structure
  - Create new file `coffee_payment/payments/services/validation_service.py`
  - Define `OrderValidationService` class with static methods
  - Import required dependencies (models, logging, settings, TmetrService)
  - _Requirements: 1.1, 2.1, 3.1_

- [x] 3.2 Implement hash validation method
  - Implement `validate_request_hash()` static method as placeholder that always returns success
  - Add logging for hash validation attempts with all request parameters
  - Return tuple of (is_valid, error_message)
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3.3 Implement order existence check method
  - Implement `check_order_existence()` static method
  - Query Order model by UUID
  - Check if order exists and validate expiration using `is_expired()` method
  - Return tuple indicating whether to create new order, error message, and existing order instance
  - Add logging for all order existence check results
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.4 Implement device online status check method
  - Implement `check_device_online_status()` static method
  - Call `TmetrService.get_device_heartbeat()` with device UUID
  - Extract heartbeat timestamp from API response
  - Calculate time difference between current time and heartbeat timestamp
  - Compare difference with configured threshold from settings
  - Handle timezone considerations in timestamp comparison
  - Handle API errors and return appropriate error messages
  - Add comprehensive logging with device UUID, heartbeat timestamp, and online/offline determination
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 3.5 Implement validation chain orchestration method
  - Implement `execute_validation_chain()` static method
  - Call validation methods sequentially: hash → order existence → device status
  - Implement early termination on first validation failure
  - Return dictionary with validation results including valid flag, error message, existing order, and should_create_new_order flag
  - Add logging for validation chain start and completion
  - _Requirements: 1.1, 2.1, 3.1, 7.1, 7.2, 7.3, 7.4_

- [x] 4. Integrate validation chain into process_payment_flow
  - Modify `process_payment_flow()` function in `coffee_payment/payments/views.py`
  - Add validation chain execution after parameter validation and before device/merchant validation
  - Extract all request parameters into dictionary for validation
  - Call `OrderValidationService.execute_validation_chain()` with request parameters
  - Handle validation failure by returning error page with appropriate message
  - Implement conditional order creation based on validation results (skip creation if existing valid order found)
  - Update logging to include validation chain results
  - _Requirements: 2.2, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 7.1, 7.4_

- [x] 5. Update PROJECT.md documentation
  - Update `coffee_payment/docs/PROJECT.md` with new validation chain description
  - Document validation sequence and integration points
  - Add information about new configuration settings
  - Document Tmetr heartbeat API endpoint
  - Update architecture diagram to include validation chain
  - _Requirements: All requirements (documentation)_

- [x] 6. Write unit tests for validation service
  - Create test file `coffee_payment/tests/test_order_validation.py`
  - Write tests for `validate_request_hash()` placeholder implementation
  - Write tests for `check_order_existence()` covering all scenarios (non-existent, existing valid, existing expired)
  - Write tests for `check_device_online_status()` covering online/offline cases and error handling
  - Write tests for `execute_validation_chain()` covering early termination and successful execution
  - Mock Tmetr API calls for predictable testing
  - Verify all tests run with 30-second timeout
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 7. Write integration tests for complete validation flow
  - Create test file `coffee_payment/tests/test_order_validation_integration.py`
  - Write test for complete flow with all validations passing
  - Write test for flow termination on each validation failure type
  - Write test for existing valid order scenario (no new order created)
  - Write test for error page rendering for each validation failure
  - Mock Tmetr API and database interactions
  - Verify all tests run with 30-second timeout
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4_
