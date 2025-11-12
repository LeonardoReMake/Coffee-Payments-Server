# Requirements Document

## Introduction

This feature introduces an order information screen that displays order details to users before they proceed to payment in Yookassa and TBank payment scenarios. The screen provides transparency by showing drink details, pricing, location, and merchant branding before the user commits to payment.

## Glossary

- **Order Info Screen**: A web page that displays order details before payment initiation
- **Payment System**: The Django-based backend application that processes coffee machine orders
- **Device**: A coffee machine registered in the system with associated merchant and payment configuration
- **Payment Scenario**: The payment provider configuration (Yookassa, TBank, or Custom) assigned to a Device
- **User**: The end customer who scans a QR code and makes a payment for a drink
- **Drink Price Response**: The successful API response containing drink name, size, and price information
- **Payment Creation Request**: The API call to create a payment in the selected payment provider

## Requirements

### Requirement 1

**User Story:** As a user purchasing a drink, I want to see complete order information before paying, so that I can verify the details and make an informed decision.

#### Acceptance Criteria

1. WHEN the Payment System receives a successful Drink Price Response, THE Order Info Screen SHALL display the merchant logo from Device.logo_url
2. WHEN the Payment System receives a successful Drink Price Response, THE Order Info Screen SHALL display the Device location
3. WHEN the Payment System receives a successful Drink Price Response, THE Order Info Screen SHALL display the drink name
4. WHEN the Payment System receives a successful Drink Price Response, THE Order Info Screen SHALL display the drink size as one of three values: маленький, средний, or большой
5. WHEN the Payment System receives a successful Drink Price Response, THE Order Info Screen SHALL display the drink price

### Requirement 2

**User Story:** As a merchant, I want to display custom information to customers on the order screen, so that I can communicate important messages or instructions.

#### Acceptance Criteria

1. WHEN the Order Info Screen is rendered, THE Payment System SHALL display the Device.client_info text field content
2. WHERE Device.client_info is empty or null, THE Order Info Screen SHALL render without displaying the client info section

### Requirement 3

**User Story:** As a user, I want to initiate payment from the order information screen, so that I can complete my purchase after reviewing the details.

#### Acceptance Criteria

1. WHEN the Order Info Screen is displayed, THE Payment System SHALL render a "Перейти к оплате" button
2. WHEN the user clicks the "Перейти к оплате" button, THE Payment System SHALL initiate a Payment Creation Request to the payment provider corresponding to the Device payment scenario
3. WHILE the Payment Creation Request is in progress, THE Order Info Screen SHALL display a loading state indicator
4. IF the Payment Creation Request succeeds, THEN THE Payment System SHALL redirect the user to the payment provider URL
5. IF the Payment Creation Request fails, THEN THE Order Info Screen SHALL display a user-friendly error message from the centralized error messages file

### Requirement 4

**User Story:** As a user on a mobile device, I want the order information screen to be responsive and easy to read, so that I can view order details comfortably on any device.

#### Acceptance Criteria

1. THE Order Info Screen SHALL be designed with a mobile-first approach
2. THE Order Info Screen SHALL render correctly on screen widths from 320 pixels to 1920 pixels
3. THE Order Info Screen SHALL maintain readability and usability across different device orientations

### Requirement 5

**User Story:** As a system administrator, I want the order information screen to only appear for specific payment scenarios, so that the user experience is appropriate for each payment provider.

#### Acceptance Criteria

1. WHERE Device.payment_scenario equals "Yookassa", THE Payment System SHALL display the Order Info Screen after receiving a successful Drink Price Response
2. WHERE Device.payment_scenario equals "TBank", THE Payment System SHALL display the Order Info Screen after receiving a successful Drink Price Response
3. WHERE Device.payment_scenario equals "Custom", THE Payment System SHALL NOT display the Order Info Screen and SHALL proceed directly to the redirect URL

### Requirement 6

**User Story:** As a developer, I want all user-facing error messages to be centralized, so that they can be easily maintained and localized.

#### Acceptance Criteria

1. THE Payment System SHALL store all user-facing error messages in a centralized messages file
2. WHEN an error occurs on the Order Info Screen, THE Payment System SHALL retrieve the error message from the centralized messages file
3. THE Order Info Screen SHALL NOT display technical error details such as stack traces, error codes, or exception messages to users

### Requirement 7

**User Story:** As a system operator, I want all order screen interactions to be logged, so that I can troubleshoot issues and monitor system behavior.

#### Acceptance Criteria

1. WHEN the Order Info Screen is rendered, THE Payment System SHALL log the event with Device ID, order details, and payment scenario
2. WHEN a user clicks the "Перейти к оплате" button, THE Payment System SHALL log the payment initiation attempt with all request parameters
3. WHEN a Payment Creation Request completes, THE Payment System SHALL log the result including success or failure status and response details
4. THE Payment System SHALL use the existing project logger for all Order Info Screen logging operations
