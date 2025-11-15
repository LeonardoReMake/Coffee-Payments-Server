# Implementation Plan

- [x] 1. Enhance API endpoint to include expiration time
  - Modify `get_order_status()` view to include `expires_at` field in JSON response
  - Add `device.client_info` field to response for status=created
  - Format `expires_at` as ISO 8601 string with timezone
  - _Requirements: 3.1, 4.2_

- [x] 2. Enhance unified order status page template
  - [x] 2.1 Add UI for status=created with payment button
    - Add "Перейти к оплате" button section
    - Add loading state for payment initiation
    - Style button consistently with existing design
    - _Requirements: 1.2, 1.4_
  
  - [x] 2.2 Add client-side expiration check
    - Parse `expires_at` from API response
    - Compare with current time on page load and during polling
    - Show expiration warning if order expired
    - Disable payment button if expired
    - _Requirements: 3.3, 3.4, 3.5_
  
  - [x] 2.3 Add payment initiation logic
    - Handle "Перейти к оплате" button click
    - Send POST request to `/v1/initiate-payment` with order_id
    - Show loading state during request
    - Handle success (redirect to payment URL)
    - Handle errors (display error message)
    - _Requirements: 1.4_
  
  - [x] 2.4 Display status-specific client info
    - Show `device.client_info` for status=created
    - Maintain existing status-specific info display for other statuses
    - Support HTML formatting in client info fields
    - _Requirements: 1.3_

- [x] 3. Modify payment flow to use unified status page
  - [x] 3.1 Update process_payment_flow() routing
    - Remove call to `show_order_info()` for Yookassa/TBank scenarios
    - Always redirect to `/v1/order-status-page?order_id=X` after order creation/validation
    - Update logging to reflect new routing
    - _Requirements: 1.1, 2.1, 2.2_
  
  - [x] 3.2 Update Custom scenario routing
    - Verify Custom scenario still executes immediately (no change needed)
    - Ensure logging is consistent
    - _Requirements: 1.1_

- [x] 4. Remove deprecated components
  - Delete `show_order_info()` view function from views.py
  - Delete `order_info_screen.html` template file
  - Verify no other code references these components
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 5. Update project documentation
  - Update PROJECT.md with new unified status page architecture
  - Update flow diagrams to reflect new routing
  - Document API changes (expires_at field)
  - Update "Основные потоки данных" section
  - _Requirements: 5.4_

- [x] 6. Write automated tests
  - [x] 6.1 Write unit tests for API changes
    - Test `get_order_status()` includes `expires_at` field
    - Test `get_order_status()` includes `client_info` field
    - Test ISO 8601 format with timezone
    - _Requirements: 4.1, 4.2_
  
  - [x] 6.2 Write unit tests for routing changes
    - Test `process_payment_flow()` redirects to unified status page
    - Test redirect URL format
    - Test for both new and existing orders
    - _Requirements: 1.1, 2.1, 2.2_
  
  - [x] 6.3 Write integration tests
    - Test full flow: QR scan → create order → show status page → initiate payment
    - Test full flow with existing order
    - Test full flow with expired order
    - Test status page polling detects status changes
    - _Requirements: 1.1, 2.1, 2.2, 3.3_
