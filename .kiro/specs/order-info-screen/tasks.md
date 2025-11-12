# Implementation Plan: Order Information Screen

- [x] 1. Create centralized user messages file
  - Create `coffee_payment/payments/user_messages.py` with ERROR_MESSAGES and INFO_MESSAGES dictionaries
  - Include all user-facing error messages for order info screen functionality
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 2. Add new fields to Device model
  - Add `logo_url` field (URLField, nullable) to Device model
  - Add `client_info` field (TextField, nullable) to Device model
  - Create and run database migration for new fields
  - _Requirements: 2.1, 2.2_

- [x] 3. Implement show_order_info view function
  - Create `show_order_info(request, device, order, drink_details)` function in `payments/views.py`
  - Extract drink information from drink_details parameter
  - Map drink size from database format (1,2,3) to Russian labels (маленький, средний, большой)
  - Format price from kopecks to rubles for display
  - Prepare context dictionary with device, order, and formatted drink information
  - Log order info screen rendering event with device ID, order ID, and payment scenario
  - Render `order_info_screen.html` template with context
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 7.1_

- [x] 4. Implement initiate_payment view function
  - Create `initiate_payment(request)` function in `payments/views.py` to handle POST requests
  - Validate order_id parameter from POST data
  - Retrieve Order instance and check if order has expired using `is_expired()` method
  - Execute payment scenario using `PaymentScenarioService.execute_scenario()`
  - Log payment initiation attempt with all request parameters
  - Return redirect to payment provider URL on success
  - Handle errors: missing order_id (400), order not found (404), expired order (400), payment creation failure (503)
  - Return JSON responses with user-friendly error messages from `user_messages.py`
  - _Requirements: 3.2, 3.3, 3.4, 3.5, 7.2, 7.3_

- [x] 5. Modify yookassa_payment_process to conditionally show order info screen
  - Modify `yookassa_payment_process()` in `payments/views.py` after order creation
  - Check if `device.payment_scenario` is 'Yookassa' or 'TBank'
  - If Yookassa or TBank: call `show_order_info()` and return its response
  - If Custom: execute payment scenario immediately using existing code path
  - Ensure order status remains 'created' when showing order info screen
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Create order_info_screen.html template
  - Create `coffee_payment/templates/payments/order_info_screen.html` file
  - Implement mobile-first HTML structure with semantic markup
  - Add logo section that displays `device.logo_url` image when available
  - Display device location, drink name, drink size, and formatted price
  - Add client info section that displays `device.client_info` text when available
  - Create "Перейти к оплате" button that triggers payment initiation
  - Include hidden order_id in template for JavaScript access
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 3.1_

- [x] 7. Implement CSS styling for order info screen
  - Add mobile-first CSS styles in `order_info_screen.html` <style> section
  - Implement responsive layout with breakpoints at 768px (tablet) and 1024px (desktop)
  - Style logo section with proper image sizing and centering
  - Style order information rows with clear labels and values
  - Style price row with emphasis (larger font, bold)
  - Style client info section with distinct visual treatment
  - Style payment button with touch-friendly size (min 44px height) and clear call-to-action appearance
  - Create loading state styles with spinner animation
  - Create error state styles with error message and retry button
  - Ensure all text has sufficient color contrast for accessibility
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 8. Implement JavaScript for payment initiation and state management
  - Add JavaScript in `order_info_screen.html` <script> section
  - Implement `initiatePayment()` function that sends POST request to `/v1/initiate-payment` endpoint
  - Include CSRF token in request headers using `getCookie('csrftoken')` helper function
  - Show loading state (hide button, show spinner) when request starts
  - Handle success response by redirecting to payment provider URL
  - Handle error response by showing error message from response and displaying retry button
  - Implement `retryPayment()` function to reset UI and allow user to try again
  - Disable payment button during loading to prevent double-clicks
  - _Requirements: 3.2, 3.3, 3.4, 3.5_

- [x] 9. Add URL pattern for initiate_payment endpoint
  - Add new URL pattern in `coffee_payment/coffee_payment/urls.py`
  - Map `/v1/initiate-payment` to `initiate_payment` view function
  - Set URL name to 'initiate_payment' for reverse URL lookup
  - _Requirements: 3.2_

- [x] 10. Update logging configuration
  - Add 'show_order_info' logger configuration in `coffee_payment/coffee_payment/settings.py`
  - Add 'initiate_payment' logger configuration in `coffee_payment/coffee_payment/settings.py`
  - Configure both loggers to use file handler with DEBUG level
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 11. Write unit tests for order info screen functionality
  - [x] 11.1 Create test file `coffee_payment/tests/test_order_info_screen.py`
    - Set up test fixtures for Device, Merchant, Order with required fields
    - Create helper functions for generating test data
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

  - [x] 11.2 Write tests for show_order_info function
    - Test order info screen renders for Yookassa scenario with all context data
    - Test order info screen renders for TBank scenario with all context data
    - Test drink size mapping (1→маленький, 2→средний, 3→большой)
    - Test price formatting from kopecks to rubles
    - Test screen renders correctly when logo_url is None
    - Test screen renders correctly when client_info is None
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2_

  - [x] 11.3 Write tests for initiate_payment function
    - Test successful payment initiation returns redirect to payment URL
    - Test order status updates to 'pending' after successful payment creation
    - Test expired order returns 400 response with appropriate error message
    - Test missing order_id parameter returns 400 response
    - Test non-existent order_id returns 404 response
    - Test payment creation failure returns 503 response with user-friendly message
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [x] 11.4 Write tests for payment flow routing
    - Test Custom scenario bypasses order info screen and redirects directly
    - Test Yookassa scenario shows order info screen instead of immediate redirect
    - Test TBank scenario shows order info screen instead of immediate redirect
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 12. Write integration tests for complete payment flow
  - [x] 12.1 Create test file `coffee_payment/tests/test_order_info_integration.py`
    - Set up test client and fixtures for end-to-end testing
    - Mock external API calls (Tmetr, Yookassa, TBank)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3_

  - [x] 12.2 Test full Yookassa payment flow
    - Simulate QR code scan to yookassa_payment_process endpoint
    - Verify order info screen is rendered with correct data
    - Simulate payment button click to initiate_payment endpoint
    - Verify redirect to Yookassa payment URL
    - Verify order status transitions: created → pending
    - _Requirements: 5.1, 3.2, 3.3, 3.4_

  - [ ]* 12.3 Test full TBank payment flow
    - Simulate QR code scan to yookassa_payment_process endpoint with TBank device
    - Verify order info screen is rendered with correct data
    - Simulate payment button click to initiate_payment endpoint
    - Verify redirect to TBank payment URL
    - Verify order status transitions: created → pending
    - _Requirements: 5.2, 3.2, 3.3, 3.4_

  - [ ]* 12.4 Test Custom scenario bypasses order info screen
    - Simulate QR code scan to yookassa_payment_process endpoint with Custom device
    - Verify immediate redirect to custom URL without showing order info screen
    - Verify order parameters are included in redirect URL
    - _Requirements: 5.3_
