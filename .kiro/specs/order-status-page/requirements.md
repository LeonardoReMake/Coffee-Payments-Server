# Requirements Document

## Introduction

This feature implements a real-time order status tracking page for the Coffee Payment Server. After completing payment in a payment system, users are automatically redirected to this page where they can monitor their order status in real-time. The page displays order details, current status with appropriate visual states, and provides status-specific actions (such as retry payment). The system polls the server every second to update the order status without page reload, ensuring a smooth user experience throughout the order lifecycle from payment verification to drink preparation completion.

## Glossary

- **Order Status Page**: A web page that displays real-time order information and status updates
- **System**: The Coffee Payment Server Django application
- **User**: A customer who has scanned a QR code and is purchasing a coffee drink
- **Order**: A coffee drink purchase request with associated payment and status information
- **Device**: A coffee machine that prepares drinks
- **Status Polling**: Automatic periodic checking of order status via REST API requests
- **Mobile First**: Design approach prioritizing mobile device display and interaction
- **HTML Support**: Ability to render HTML tags in client information fields

## Requirements

### Requirement 1: Order Status Page Access

**User Story:** As a user, I want to be automatically redirected to the order status page after completing payment, so that I can track my order progress.

#### Acceptance Criteria

1. WHEN the order status page loads, THE System SHALL retrieve the order_id from the URL query parameters
2. WHEN the order_id is retrieved, THE System SHALL load all order information from the database
3. IF the order_id is missing from query parameters, THEN THE System SHALL display an error message to the user
4. IF the order does not exist in the database, THEN THE System SHALL display an error message to the user

### Requirement 2: Order Information Display

**User Story:** As a user, I want to see complete information about my order, so that I can verify the details of my purchase.

#### Acceptance Criteria

1. THE System SHALL display the merchant logo from Device.logo_url on the order status page
2. THE System SHALL display the coffee machine address from Device.location on the order status page
3. THE System SHALL display the drink name on the order status page
4. THE System SHALL display the drink size as "маленький" for size 1, "средний" for size 2, or "большой" for size 3
5. THE System SHALL display the drink price in rubles on the order status page
6. IF Device.logo_url is not set, THEN THE System SHALL display the page without a logo

### Requirement 3: Status-Specific Display for Pending Status

**User Story:** As a user, I want to see that my payment is being verified when the order status is pending, so that I know the system is processing my payment.

#### Acceptance Criteria

1. WHEN Order.status equals "pending", THE System SHALL display a loading state visual indicator
2. WHEN Order.status equals "pending", THE System SHALL display the description "Проверяем оплату заказа..."
3. WHEN Order.status equals "pending", THE System SHALL display the content from Device.client_info_pending field
4. WHEN Device.client_info_pending contains HTML tags, THE System SHALL render the HTML tags correctly

### Requirement 4: Status-Specific Display for Paid Status

**User Story:** As a user, I want to see confirmation that my payment was successful and drink preparation is starting, so that I know my order is progressing.

#### Acceptance Criteria

1. WHEN Order.status equals "paid", THE System SHALL display a success state visual indicator
2. WHEN Order.status equals "paid", THE System SHALL display the description "Заказ успешно оплачен, начинаем готовить"
3. WHEN Order.status equals "paid", THE System SHALL display the content from Device.client_info_paid field
4. WHEN Device.client_info_paid contains HTML tags, THE System SHALL render the HTML tags correctly

### Requirement 5: Status-Specific Display for Not Paid Status

**User Story:** As a user, I want to see that my payment failed and have the option to retry, so that I can complete my purchase.

#### Acceptance Criteria

1. WHEN Order.status equals "not_paid", THE System SHALL display an error state visual indicator
2. WHEN Order.status equals "not_paid", THE System SHALL display the description "Оплата не прошла"
3. WHEN Order.status equals "not_paid", THE System SHALL display a "Повторить оплату" button
4. WHEN the user clicks the "Повторить оплату" button, THE System SHALL create a new payment request using the same logic as the order_info_screen
5. WHEN Order.status equals "not_paid", THE System SHALL display the content from Device.client_info_not_paid field
6. WHEN Device.client_info_not_paid contains HTML tags, THE System SHALL render the HTML tags correctly

### Requirement 6: Status-Specific Display for Make Pending Status

**User Story:** As a user, I want to see that my drink is being prepared, so that I know when to expect my order to be ready.

#### Acceptance Criteria

1. WHEN Order.status equals "make_pending", THE System SHALL display a loading state visual indicator
2. WHEN Order.status equals "make_pending", THE System SHALL display the description "Готовим напиток..."
3. WHEN Order.status equals "make_pending", THE System SHALL display the content from Device.client_info_make_pending field
4. WHEN Device.client_info_make_pending contains HTML tags, THE System SHALL render the HTML tags correctly

### Requirement 7: Status-Specific Display for Successful Status

**User Story:** As a user, I want to see confirmation that my drink is ready, so that I know I can collect it from the machine.

#### Acceptance Criteria

1. WHEN Order.status equals "successful", THE System SHALL display a success state visual indicator
2. WHEN Order.status equals "successful", THE System SHALL display the description "Напиток готов"
3. WHEN Order.status equals "successful", THE System SHALL display the content from Device.client_info_successful field
4. WHEN Device.client_info_successful contains HTML tags, THE System SHALL render the HTML tags correctly

### Requirement 8: Real-Time Status Updates

**User Story:** As a user, I want the page to automatically update when my order status changes, so that I don't need to manually refresh the page.

#### Acceptance Criteria

1. THE System SHALL send a REST API request to check order status every 1 second
2. WHEN a new order status is received from the API, THE System SHALL update the user interface without reloading the page
3. THE System SHALL apply smooth transitions when changing between different status displays
4. THE System SHALL continue polling while the order status is "pending", "paid", or "make_pending"
5. WHEN the order status becomes "successful", "not_paid", or "failed", THE System SHALL stop polling

### Requirement 9: Mobile-First Responsive Design

**User Story:** As a user, I want the order status page to work well on my mobile device, so that I can track my order from my phone.

#### Acceptance Criteria

1. THE System SHALL design the order status page with mobile-first principles
2. THE System SHALL ensure the page displays correctly on screen widths from 320 pixels to 1920 pixels
3. THE System SHALL ensure all interactive elements are easily tappable on touch devices with minimum 44 pixel touch targets
4. THE System SHALL ensure text is readable without zooming on mobile devices with minimum 16 pixel font size for body text

### Requirement 10: Error Handling and User Messages

**User Story:** As a user, I want to see clear, understandable error messages if something goes wrong, so that I know what happened without seeing technical details.

#### Acceptance Criteria

1. THE System SHALL store all user-facing error messages in the centralized user_messages.py file
2. THE System SHALL display user-friendly error messages without technical details such as stack traces or exception messages
3. WHEN a network error occurs during status polling, THE System SHALL display an error message to the user
4. WHEN the API returns an error response, THE System SHALL display an error message to the user
5. THE System SHALL log technical error details for debugging purposes without displaying them to users
