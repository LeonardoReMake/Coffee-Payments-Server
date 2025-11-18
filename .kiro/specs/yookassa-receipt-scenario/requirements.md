# Requirements Document

## Introduction

This document specifies requirements for implementing a new payment scenario called YookassaReceipt. This scenario extends the existing Yookassa payment scenario by adding fiscal receipt generation capabilities. The system will collect customer email addresses and send receipt data to YooKassa API for fiscal compliance.

## Glossary

- **Payment_System**: The Coffee Payments Server that processes payments for coffee vending machines
- **YookassaReceipt_Scenario**: A new payment scenario that extends Yookassa with receipt generation
- **Merchant_Credentials**: Configuration data stored per merchant for each payment scenario
- **Receipt_Object**: JSON structure containing fiscal receipt data sent to YooKassa API
- **Order_Status_Page**: Web page displaying order information and payment controls
- **Drink_Meta**: JSON field in Drink model containing receipt-specific data
- **Email_Field**: Input field on Order_Status_Page for customer email address

## Requirements

### Requirement 1

**User Story:** As a merchant, I want to configure receipt generation settings for my devices, so that I can comply with fiscal regulations

#### Acceptance Criteria

1. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL store is_receipt_mandatory flag in Merchant_Credentials
2. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL store tax_system_code in Merchant_Credentials
3. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL allow optional storage of timezone in Merchant_Credentials
4. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL allow optional storage of vat_code in Merchant_Credentials
5. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL allow optional storage of measure in Merchant_Credentials
6. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL allow optional storage of payment_subject in Merchant_Credentials
7. WHERE YookassaReceipt_Scenario is selected, THE Payment_System SHALL allow optional storage of payment_mode in Merchant_Credentials

### Requirement 2

**User Story:** As a customer, I want to provide my email address for receipt delivery, so that I can receive a fiscal receipt for my purchase

#### Acceptance Criteria

1. WHEN Order_Status_Page loads, IF payment_scenario equals YookassaReceipt AND order status equals created, THEN THE Payment_System SHALL display Email_Field
2. WHEN customer enters email, THE Payment_System SHALL validate email format using standard email validation
3. WHERE is_receipt_mandatory equals true, THE Payment_System SHALL require Email_Field completion before enabling payment button
4. WHERE is_receipt_mandatory equals false, THE Payment_System SHALL allow payment without Email_Field completion
5. WHEN Email_Field contains invalid email format, THE Payment_System SHALL display validation error message

### Requirement 3

**User Story:** As a system administrator, I want drink items to store receipt metadata, so that correct fiscal data is sent to YooKassa

#### Acceptance Criteria

1. THE Payment_System SHALL add meta field of type JSON to Drink model
2. WHERE meta field exists, THE Payment_System SHALL store vat_code in Drink meta
3. WHERE meta field exists, THE Payment_System SHALL store measure in Drink meta
4. WHERE meta field exists, THE Payment_System SHALL store payment_subject in Drink meta
5. WHERE meta field exists, THE Payment_System SHALL store payment_mode in Drink meta
6. THE Payment_System SHALL change Drink primary key from UUID to integer type

### Requirement 4

**User Story:** As a system, I want to construct receipt objects with proper fallback logic, so that receipts are generated even when some data is missing

#### Acceptance Criteria

1. WHEN constructing Receipt_Object, IF vat_code exists in Drink_Meta, THEN THE Payment_System SHALL use vat_code from Drink_Meta
2. WHEN constructing Receipt_Object, IF vat_code does not exist in Drink_Meta AND vat_code exists in Merchant_Credentials, THEN THE Payment_System SHALL use vat_code from Merchant_Credentials
3. WHEN constructing Receipt_Object, IF measure exists in Drink_Meta, THEN THE Payment_System SHALL use measure from Drink_Meta
4. WHEN constructing Receipt_Object, IF measure does not exist in Drink_Meta AND measure exists in Merchant_Credentials, THEN THE Payment_System SHALL use measure from Merchant_Credentials
5. WHEN constructing Receipt_Object, IF payment_subject exists in Drink_Meta, THEN THE Payment_System SHALL use payment_subject from Drink_Meta
6. WHEN constructing Receipt_Object, IF payment_subject does not exist in Drink_Meta AND payment_subject exists in Merchant_Credentials, THEN THE Payment_System SHALL use payment_subject from Merchant_Credentials
7. WHEN constructing Receipt_Object, IF payment_mode exists in Drink_Meta, THEN THE Payment_System SHALL use payment_mode from Drink_Meta
8. WHEN constructing Receipt_Object, IF payment_mode does not exist in Drink_Meta AND payment_mode exists in Merchant_Credentials, THEN THE Payment_System SHALL use payment_mode from Merchant_Credentials
9. WHEN constructing Receipt_Object, IF field does not exist in Drink_Meta AND field does not exist in Merchant_Credentials, THEN THE Payment_System SHALL exclude field from Receipt_Object

### Requirement 5

**User Story:** As a system, I want to send receipt data to YooKassa when creating payments, so that fiscal receipts are generated for customers

#### Acceptance Criteria

1. WHEN customer initiates payment, IF Email_Field contains valid email, THEN THE Payment_System SHALL include Receipt_Object in YooKassa payment request
2. WHEN creating Receipt_Object, THE Payment_System SHALL set customer email to Email_Field value
3. WHEN creating Receipt_Object, THE Payment_System SHALL set item description to drink name
4. WHEN creating Receipt_Object, THE Payment_System SHALL set item amount value to drink price in decimal format
5. WHEN creating Receipt_Object, THE Payment_System SHALL set item amount currency to RUB
6. WHEN creating Receipt_Object, THE Payment_System SHALL set item quantity to 1
7. WHEN creating Receipt_Object, THE Payment_System SHALL set internet field to false
8. WHEN creating Receipt_Object, IF tax_system_code exists in Merchant_Credentials, THEN THE Payment_System SHALL include tax_system_code in Receipt_Object
9. WHEN creating Receipt_Object, IF timezone exists in Merchant_Credentials, THEN THE Payment_System SHALL include timezone in Receipt_Object

### Requirement 6

**User Story:** As a system administrator, I want receipt data to be persisted in the database, so that I can track and audit fiscal receipts

#### Acceptance Criteria

1. WHEN payment with receipt is created successfully, THE Payment_System SHALL create Receipt record in database
2. WHEN creating Receipt record, THE Payment_System SHALL store customer email
3. WHEN creating Receipt record, THE Payment_System SHALL store drink_no
4. WHEN creating Receipt record, THE Payment_System SHALL store amount
5. WHEN creating Receipt record, THE Payment_System SHALL store timestamp with timezone
6. WHEN creating Receipt record, THE Payment_System SHALL store complete receipt data in JSON format

### Requirement 7

**User Story:** As a developer, I want YookassaReceipt scenario to reuse Yookassa logic, so that implementation is maintainable and consistent

#### Acceptance Criteria

1. THE Payment_System SHALL implement YookassaReceipt_Scenario as extension of Yookassa scenario
2. WHEN YookassaReceipt_Scenario processes payment, THE Payment_System SHALL execute all Yookassa scenario logic
3. WHEN YookassaReceipt_Scenario processes payment, THE Payment_System SHALL add receipt generation logic to Yookassa flow
4. THE Payment_System SHALL add YookassaReceipt to PAYMENT_SCENARIOS list in settings
