# Implementation Plan

- [x] 1. Add status-specific client info fields to Device model
  - Create migration to add client_info_pending, client_info_paid, client_info_not_paid, client_info_make_pending, and client_info_successful fields to Device model
  - All fields should be TextField, nullable, with help text indicating HTML support
  - Run migration to apply database changes
  - _Requirements: 2.1, 3.3, 4.3, 5.5, 6.3, 7.3_

- [x] 2. Add status descriptions to centralized user messages
  - Add STATUS_DESCRIPTIONS dictionary to user_messages.py with descriptions for all order statuses (pending, paid, not_paid, make_pending, successful, failed)
  - Add new error message 'status_update_failed' for polling failures
  - Add new info message 'loading_order_info' for initial page load
  - _Requirements: 3.2, 4.2, 5.2, 6.2, 7.2, 10.1_

- [x] 3. Implement API endpoint for order status retrieval
  - Create get_order_status view function in views.py that accepts order_id as URL parameter
  - Implement database query with select_related('device') to fetch order and device data
  - Map order size integer to Russian label (маленький/средний/большой)
  - Convert price from kopecks to rubles for JSON response
  - Return JSON response with order_id, status, drink_name, drink_size, price, and device fields (location, logo_url, all client_info fields)
  - Handle Order.DoesNotExist exception and return 404 with error message from ERROR_MESSAGES
  - Add logging for successful requests and errors
  - _Requirements: 1.2, 1.3, 1.5, 2.2, 2.3, 2.4, 2.5, 8.1, 10.5_

- [x] 4. Implement view function for order status page rendering
  - Create show_order_status_page view function in views.py
  - Extract order_id from query parameters
  - Validate order_id is present, return error page if missing
  - Verify order exists in database, return error page if not found
  - Render order_status_page.html template with order_id in context
  - Add logging for page rendering and errors
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 10.5_

- [x] 5. Create order status page HTML template
  - Create templates/payments/order_status_page.html with mobile-first responsive design
  - Implement CSS for screen widths 320px to 1920px with breakpoints at 768px and 1024px
  - Create sections for logo, order information (location, drink name, size, price), status display, and client info
  - Implement three UI states: loading (spinner), status-specific (with icons), and error (with retry button)
  - Add hidden input field to store order_id for JavaScript access
  - Ensure minimum 44px touch targets for mobile devices
  - Ensure minimum 16px font size for body text
  - Support high contrast mode and reduced motion preferences
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 9.1, 9.2, 9.3, 9.4_

- [x] 6. Implement JavaScript for initial order data fetch
  - Add fetchOrderStatus async function that calls GET /v1/order-status/<order_id>
  - Parse JSON response and extract order data
  - Implement error handling for network failures and API errors
  - Call fetchOrderStatus on page load with order_id from hidden input
  - Display loading state during initial fetch
  - _Requirements: 1.2, 1.3, 8.1, 10.3, 10.4_

- [x] 7. Implement JavaScript for UI updates based on order status
  - Create updateUI function that accepts order data object
  - Update order information display (logo, location, drink name, size, price)
  - Implement status-specific display logic for pending, paid, not_paid, make_pending, and successful statuses
  - Show appropriate icon (loading spinner for pending/make_pending, success icon for paid/successful, error icon for not_paid)
  - Display status description from STATUS_DESCRIPTIONS
  - Render HTML content in client info fields using innerHTML
  - Show/hide "Повторить оплату" button based on status (visible only for not_paid)
  - Apply smooth CSS transitions when changing states
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.6, 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 8.2, 8.3_

- [x] 8. Implement JavaScript for status polling
  - Create startPolling function that calls fetchOrderStatus every 1 second using setInterval
  - Call updateUI with fetched data on each poll
  - Implement logic to stop polling when status is 'successful', 'not_paid', or 'failed'
  - Continue polling for 'pending', 'paid', and 'make_pending' statuses
  - Handle polling errors by displaying error message without stopping the poll
  - Start polling automatically after initial page load
  - _Requirements: 8.1, 8.2, 8.4, 8.5, 10.3_

- [x] 9. Implement retry payment functionality
  - Create retryPayment JavaScript function that sends POST request to /v1/initiate-payment
  - Include order_id in request body as JSON
  - Get CSRF token from cookies using getCookie helper function
  - Show loading state during payment creation
  - Handle successful response by redirecting to payment URL
  - Handle error response by displaying error message
  - Attach retryPayment function to "Повторить оплату" button click event
  - Reuse existing initiate_payment view logic from order_info_screen
  - _Requirements: 5.3, 5.4, 10.3, 10.4_

- [x] 10. Add URL routes for new endpoints
  - Add route for order status page: path('v1/order-status-page', views.show_order_status_page, name='order_status_page')
  - Add route for order status API: path('v1/order-status/<str:order_id>', views.get_order_status, name='get_order_status')
  - Update coffee_payment/urls.py with new routes
  - _Requirements: 1.1, 8.1_

- [x] 11. Update payment system redirect URLs
  - Modify Yookassa payment creation in yookassa_service.py to set return_url to order status page
  - Modify TBank payment creation in t_bank_service.py to set success_url to order status page
  - Include order_id as query parameter in redirect URLs
  - Test redirect flow from payment system to order status page
  - _Requirements: 1.1_

- [x] 12. Register new Device fields in Django Admin
  - Update admin.py to display new client_info fields in Device admin interface
  - Add fieldsets to group status-specific client info fields together
  - Add help text to indicate HTML formatting support
  - _Requirements: 2.1, 3.3, 4.3, 5.5, 6.3, 7.3_

- [x] 13. Update PROJECT.md documentation
  - Add section describing order status page functionality
  - Document new Device model fields
  - Document new API endpoints and URL routes
  - Update architecture diagram to include order status page flow
  - Document payment system redirect configuration
  - _Requirements: All requirements_
