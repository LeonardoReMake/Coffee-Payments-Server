# Implementation Plan

- [x] 1. Update Order and Device models
  - [x] 1.1 Add `make_failed` status to Order.status choices
    - Modify `coffee_payment/payments/models.py`
    - Add `('make_failed', 'Make Failed')` to Order.status choices list
    - _Requirements: 2.1_
  
  - [x] 1.2 Add `client_info_make_failed` field to Device model
    - Modify `coffee_payment/payments/models.py`
    - Add TextField with null=True, blank=True, and appropriate help_text
    - _Requirements: 3.1, 3.2_
  
  - [x] 1.3 Create and apply database migration
    - Run `python manage.py makemigrations payments`
    - Review generated migration file
    - Run `python manage.py migrate payments`
    - _Requirements: 2.1, 3.1_

- [x] 2. Update user messages
  - [x] 2.1 Add `make_failed` status description to STATUS_DESCRIPTIONS
    - Modify `coffee_payment/payments/user_messages.py`
    - Add entry: `'make_failed': 'Не удалось отправить команду на приготовление. Пожалуйста, обратитесь в поддержку.'`
    - _Requirements: 2.2_

- [x] 3. Update webhook handler for error handling
  - [x] 3.1 Wrap send_make_command in try-except block
    - Modify `yookassa_payment_result_webhook()` in `coffee_payment/payments/views.py`
    - Add try-except around `tmetr_service.send_make_command()` call
    - Catch `requests.RequestException` for network/API errors
    - Catch general `Exception` for unexpected errors
    - _Requirements: 1.1, 4.1, 4.2_
  
  - [x] 3.2 Set order status to make_failed on error
    - In except blocks, set `order.status = 'make_failed'`
    - Save order with `order.save(update_fields=['status'])`
    - _Requirements: 1.1, 4.2_
  
  - [x] 3.3 Add comprehensive error logging
    - Log error message with order ID, device UUID, and all request parameters
    - Use `log_error()` with level 'ERROR'
    - Include status transition in log message (e.g., "paid → make_failed")
    - _Requirements: 1.4, 4.3_
  
  - [x] 3.4 Return HTTP 200 after setting make_failed status
    - Return `HttpResponse(status=200)` in except blocks
    - Prevents payment system from retrying webhook
    - _Requirements: 4.4_

- [x] 4. Update API endpoint for order status
  - [x] 4.1 Add client_info_make_failed to get_order_status response
    - Modify `get_order_status()` in `coffee_payment/payments/views.py`
    - Add `'client_info_make_failed': order.device.client_info_make_failed` to device dict in response
    - _Requirements: 2.4, 3.3_

- [x] 5. Update Order Status Page frontend
  - [x] 5.1 Add make_failed to STATUS_DESCRIPTIONS in JavaScript
    - Modify `coffee_payment/templates/payments/order_status_page.html`
    - Add entry in STATUS_DESCRIPTIONS object
    - _Requirements: 2.3_
  
  - [x] 5.2 Add make_failed case to updateUI switch statement
    - Set status icon to '⚠' with error-icon class
    - Display client_info_make_failed if available
    - Hide payment and retry buttons
    - _Requirements: 2.3, 3.3_
  
  - [x] 5.3 Add make_failed to polling stop condition
    - Update array in startPolling function to include 'make_failed'
    - Ensures polling stops for terminal status
    - _Requirements: 1.3_

- [x] 6. Write unit tests
  - [x] 6.1 Test Order model with make_failed status
    - Create test in `coffee_payment/tests/test_make_failed_status.py`
    - Test setting and saving make_failed status
    - _Requirements: 2.1_
  
  - [ ]* 6.2 Test Device model client_info_make_failed field
    - Test setting field with text and HTML
    - Test null/blank values
    - _Requirements: 3.1, 3.2_
  
  - [x] 6.3 Test webhook handler error scenarios
    - Mock Tmetr API errors (RequestException)
    - Mock unexpected errors (Exception)
    - Verify status changes to make_failed
    - Verify HTTP 200 response
    - Verify error logging
    - _Requirements: 1.1, 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 6.4 Test get_order_status API includes make_failed info
    - Verify client_info_make_failed in JSON response
    - _Requirements: 3.3_

- [ ]* 7. Write integration tests
  - [ ]* 7.1 Test full payment flow with Tmetr failure
    - Create order, initiate payment, mock webhook
    - Mock Tmetr API error
    - Verify order status becomes make_failed
    - _Requirements: 1.1, 4.1, 4.2_
  
  - [ ]* 7.2 Test Order Status Page displays make_failed correctly
    - Create order with make_failed status
    - Request order status API
    - Verify response includes correct data
    - _Requirements: 2.3, 3.3_
