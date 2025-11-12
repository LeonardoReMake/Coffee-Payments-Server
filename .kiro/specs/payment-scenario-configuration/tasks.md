# Implementation Plan

- [x] 1. Configure payment scenarios in Django settings
  - Add PAYMENT_SCENARIOS list with ['Yookassa', 'TBank', 'Custom']
  - Add DEFAULT_PAYMENT_SCENARIO = 'Yookassa'
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Create database models and migrations
  - [x] 2.1 Add payment_scenario field to Device model
    - Add CharField with max_length=50, default='Yookassa'
    - Add clean() method to validate scenario against PAYMENT_SCENARIOS
    - Create and apply migration
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 2.2 Create MerchantCredentials model
    - Create model with merchant FK, scenario CharField, credentials JSONField
    - Add unique_together constraint for (merchant, scenario)
    - Add __str__ method and Meta configuration
    - Create and apply migration
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 2.3 Register models in Django Admin
    - Register MerchantCredentials in admin.py
    - Configure admin display fields
    - _Requirements: 3.1_

- [x] 3. Implement PaymentScenarioService
  - [x] 3.1 Create payment_scenario_service.py file
    - Create PaymentScenarioService class with static methods
    - Implement get_merchant_credentials() method
    - Add error handling for missing credentials
    - Add logging for all operations
    - _Requirements: 3.5, 4.1, 4.2, 6.2_
  
  - [x] 3.2 Implement execute_scenario() method
    - Add logic to route to appropriate scenario handler
    - Implement error handling and logging
    - _Requirements: 4.1, 4.3, 6.1, 6.3_
  
  - [x] 3.3 Implement execute_yookassa_scenario() method
    - Get Yookassa credentials from MerchantCredentials
    - Call modified yookassa_service.create_payment() with credentials
    - Update Order status to 'pending' on success
    - Handle errors and update Order status to 'failed'
    - _Requirements: 4.3, 4.4, 4.5, 6.3, 6.4_
  
  - [x] 3.4 Implement execute_tbank_scenario() method
    - Get TBank credentials from MerchantCredentials
    - Call modified t_bank_service with credentials
    - Update Order status to 'pending' on success
    - Handle errors and update Order status to 'failed'
    - _Requirements: 4.3, 4.4, 4.5, 6.3, 6.4_
  
  - [x] 3.5 Implement execute_custom_scenario() method
    - Validate Device.redirect_url is not empty
    - Build redirect URL with order parameters
    - Return HttpResponseRedirect
    - Handle missing redirect_url error
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.3, 6.4_

- [x] 4. Modify existing payment services
  - [x] 4.1 Update yookassa_service.py
    - Modify create_payment() to accept credentials parameter
    - Use credentials['account_id'] and credentials['secret_key'] instead of hardcoded values
    - Maintain backward compatibility if needed
    - _Requirements: 4.3, 4.4_
  
  - [x] 4.2 Update t_bank_service.py
    - Modify create_payment_api() to accept credentials parameter
    - Use credentials from parameter instead of settings
    - Update process_payment() to use credentials
    - _Requirements: 4.3, 4.5_

- [x] 5. Integrate PaymentScenarioService into views
  - [x] 5.1 Modify yookassa_payment_process view
    - After creating Order with status='created', call PaymentScenarioService.execute_scenario()
    - Remove direct call to yookassa_service.create_payment()
    - Add error handling for ValueError (missing credentials)
    - Update logging to include scenario information
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.1, 6.3, 6.4_
  
  - [x] 5.2 Update error messages
    - Add specific error message for missing credentials
    - Add specific error message for missing redirect_url in Custom scenario
    - _Requirements: 4.5, 5.4_

- [x] 6. Write tests
  - [x] 6.1 Write model tests
    - Test Device.payment_scenario validation
    - Test MerchantCredentials creation and unique constraint
    - Test MerchantCredentials JSON field storage
    - _Requirements: 2.3, 3.1, 3.2_
  
  - [x] 6.2 Write PaymentScenarioService unit tests
    - Test get_merchant_credentials() success and failure cases
    - Test execute_scenario() for each scenario type
    - Test error handling for missing credentials
    - Test error handling for missing redirect_url
    - _Requirements: 3.5, 4.1, 4.2, 4.5, 5.3, 5.4_
  
  - [x] 6.3 Write integration tests
    - Test full payment flow for Yookassa scenario
    - Test full payment flow for TBank scenario
    - Test full payment flow for Custom scenario
    - Test error cases (missing credentials, invalid scenario)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4_

- [x] 7. Create initial data and documentation
  - [x] 7.1 Create data migration for existing devices
    - Set payment_scenario='Yookassa' for all existing devices (already default)
    - _Requirements: 1.3, 2.2_
  
  - [x] 7.2 Update project documentation
    - Document new models in PROJECT.md
    - Document configuration steps for adding credentials
    - Add examples of credentials JSON structure
    - _Requirements: 3.1, 3.2, 3.3_
