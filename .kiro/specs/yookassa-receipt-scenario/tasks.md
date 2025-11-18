# Implementation Plan

- [x] 1. Update Drink model and create migrations
  - Add meta JSON field to Drink model for storing receipt metadata (vat_code, measure, payment_subject, payment_mode)
  - Change Drink primary key from UUID to Integer to match device data format
  - Create and test database migration for Drink model changes
  - Update Django admin interface to support new Drink fields
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 2. Enhance Receipt model
  - Add drink_no field to Receipt model
  - Add amount field to Receipt model
  - Add receipt_data JSON field to Receipt model
  - Add created_at timestamp field to Receipt model
  - Create database migration for Receipt model enhancements
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 3. Implement YookassaReceiptService
- [x] 3.1 Create service file and basic structure
  - Create yookassa_receipt_service.py in payments/services/
  - Implement YookassaReceiptService class with static methods
  - Add logging imports and setup
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 3.2 Implement receipt object builder
  - Implement build_receipt_object method with fallback logic
  - Add helper method for field fallback (drink_meta → credentials → exclude)
  - Implement receipt structure according to Yookassa API format
  - Add logging for fallback usage and receipt construction
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

- [x] 3.3 Implement payment creation with receipt
  - Implement create_payment_with_receipt method
  - Integrate with existing yookassa_service.create_payment
  - Add receipt object to payment request when email provided
  - Handle cases where email is not provided (skip receipt)
  - Add comprehensive logging for payment creation with receipt data
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9_

- [x] 3.4 Implement receipt record persistence
  - Implement save_receipt_record method
  - Create Receipt model instance with all required fields
  - Store complete receipt_data JSON for audit trail
  - Add error handling for database operations
  - Add logging for receipt record creation
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 4. Extend PaymentScenarioService
- [x] 4.1 Add YookassaReceipt scenario handler
  - Implement execute_yookassa_receipt_scenario method
  - Get YookassaReceipt credentials from MerchantCredentials
  - Call YookassaReceiptService.create_payment_with_receipt
  - Call YookassaReceiptService.save_receipt_record after successful payment
  - Handle missing credentials error
  - Add logging for scenario execution
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 4.2 Update execute_scenario routing
  - Add YookassaReceipt case to execute_scenario method
  - Route to execute_yookassa_receipt_scenario when scenario is YookassaReceipt
  - Pass email parameter from request to scenario handler
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 5. Update order status page template
- [x] 5.1 Add email input HTML section
  - Add email input field with label
  - Add email validation error message element
  - Add email hint message element for mandatory cases
  - Add proper HTML attributes (type, placeholder, autocomplete)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5.2 Add email input CSS styles
  - Style email section container
  - Style email label
  - Style email input field with focus states
  - Style invalid email state with red border
  - Style error and hint messages
  - Ensure mobile-first responsive design
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5.3 Implement email validation JavaScript
  - Add validateEmail function with regex pattern
  - Add email input event listener for real-time validation
  - Show/hide error message based on validation
  - Add/remove invalid CSS class based on validation
  - _Requirements: 2.2, 2.5_

- [x] 5.4 Implement conditional email display logic
  - Add updateUIForYookassaReceipt function
  - Show email section only for YookassaReceipt scenario and created status
  - Show/hide mandatory hint based on is_receipt_mandatory flag
  - Enable/disable payment button based on email validation and mandatory flag
  - _Requirements: 2.1, 2.3, 2.4_

- [x] 5.5 Update payment initiation to include email
  - Modify initiatePayment function to get email from input
  - Validate email before sending request
  - Include email in POST request body to /v1/initiate-payment
  - Handle validation errors with user-friendly alerts
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Update API endpoints
- [x] 6.1 Modify get_order_status endpoint
  - Add payment_scenario to response JSON
  - Add is_receipt_mandatory to response JSON
  - Get is_receipt_mandatory from YookassaReceipt credentials
  - Handle missing credentials gracefully (default to false)
  - _Requirements: 1.1, 2.1, 2.3, 2.4_

- [x] 6.2 Modify initiate_payment endpoint
  - Parse email parameter from request body (JSON and form data)
  - Validate email format on server side
  - Pass email to PaymentScenarioService.execute_yookassa_receipt_scenario
  - Add error handling for invalid email format
  - Add logging for email parameter
  - _Requirements: 2.1, 2.2, 2.5, 5.1_

- [x] 7. Update settings and configuration
  - Add YookassaReceipt to PAYMENT_SCENARIOS list in settings.py
  - Document YookassaReceipt credentials structure in comments
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 7.4_

- [x] 8. Update user messages
  - Add email validation error messages to user_messages.py
  - Add receipt-related error messages
  - Ensure messages are user-friendly and in Russian
  - _Requirements: 2.5_

- [x] 9. Update Django admin
  - Register Drink model with meta field display
  - Update Receipt model admin to show new fields
  - Add inline editing for Drink meta JSON
  - Add MerchantCredentials admin with YookassaReceipt example
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 10. Update PROJECT.md documentation
  - Add YookassaReceipt scenario section
  - Document email collection flow
  - Document receipt metadata structure
  - Document fallback logic for receipt fields
  - Add configuration examples for YookassaReceipt credentials
  - Update payment flow diagram to include receipt generation
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 11. Write unit tests
  - Test build_receipt_object with drink_meta values
  - Test build_receipt_object with credential fallback
  - Test build_receipt_object excludes missing fields
  - Test email validation (valid and invalid formats)
  - Test receipt mandatory validation
  - Test receipt optional validation
  - Test save_receipt_record creates correct database entry
  - Test Drink model with integer ID
  - _Requirements: All requirements_

- [ ] 12. Write integration tests
  - Test full payment flow with receipt (QR scan to receipt creation)
  - Test payment flow without email (optional scenario)
  - Test missing credentials error handling
  - Test Yookassa API integration with receipt data
  - _Requirements: All requirements_
