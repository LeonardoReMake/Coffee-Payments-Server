# Implementation Plan

- [x] 1. Add configuration settings for background payment checking
  - Add PAYMENT_CHECK_INTERVAL_S, FAST_TRACK_LIMIT_S, FAST_TRACK_INTERVAL_S, SLOW_TRACK_INTERVAL_S, PAYMENT_ATTEMPTS_LIMIT, PAYMENT_API_TIMEOUT_S to settings.py
  - Add Celery configuration (CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_BEAT_SCHEDULE)
  - _Requirements: 3.1, 4.3, 5.1, 5.3, 6.1, 6.2, 7.1, 8.1_

- [x] 2. Create database migration for Order model extensions
  - Add payment_started_at DateTimeField (nullable)
  - Add next_check_at DateTimeField (nullable)
  - Add last_check_at DateTimeField (nullable)
  - Add check_attempts IntegerField with default=0
  - Add failed_presentation_desc TextField (nullable)
  - Add 'manual_make' to status choices
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1_

  - [x] 2.1 Write property test for Order field initialization
    - **Property 1: Order initialization sets default values**
    - **Validates: Requirements 1.1**

- [ ]* 2.2 Write property test for timezone-aware timestamps
  - **Property 2: Timezone-aware timestamp management**
  - **Validates: Requirements 1.2, 1.3, 1.4, 3.4**

- [x] 3. Update Order model in models.py
  - Update Order class with new fields
  - Ensure check_attempts defaults to 0
  - Add 'manual_make' to status choices
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1_

- [x] 4. Create PaymentStatusService
  - Create payments/services/payment_status_service.py
  - Implement check_payment_status() method to query Yookassa API
  - Implement process_payment_status() method with time-based logic
  - Implement handle_check_error() method with retry logic
  - Apply 3-second timeout to API calls
  - Log all API request parameters
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 8.1, 8.2, 8.3, 9.1, 9.2, 10.1, 10.2_

- [ ]* 4.1 Write property test for Yookassa API integration
  - **Property 10: Yookassa scenarios trigger API calls**
  - **Validates: Requirements 4.1, 4.2**

  - [x] 4.2 Write property test for API timeout
    - **Property 11: Payment API calls respect timeout**
    - **Validates: Requirements 4.3**

- [ ]* 4.3 Write property test for non-Yookassa scenarios
  - **Property 12: Non-Yookassa scenarios skip payment checks**
  - **Validates: Requirements 4.4**

  - [x] 4.4 Write property test for network error retry logic
    - **Property 13: Network errors trigger retry within limit**
    - **Validates: Requirements 5.1, 5.2**

  - [x] 4.5 Write property test for exhausted retries
    - **Property 14: Exhausted retries mark order as failed**
    - **Validates: Requirements 5.3, 5.4, 5.5**

  - [x] 4.6 Write property test for pending fast track
    - **Property 15: Pending status uses fast track within limit**
    - **Validates: Requirements 6.1, 6.3**

  - [x] 4.7 Write property test for pending slow track
    - **Property 16: Pending status uses slow track beyond limit**
    - **Validates: Requirements 6.2, 6.3**

  - [x] 4.8 Write property test for fast track success
    - **Property 17: Fast track success triggers drink preparation**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x] 4.9 Write property test for delayed success
    - **Property 4: Delayed payment success triggers manual make**
    - **Validates: Requirements 2.1, 8.1**

  - [x] 4.10 Write property test for canceled payments
    - **Property 18: Canceled payments mark order as not paid**
    - **Validates: Requirements 9.1, 9.2**

- [ ]* 4.11 Write property test for waiting_for_capture
  - **Property 19: Waiting for capture marks order as failed**
  - **Validates: Requirements 10.1, 10.2**

- [ ]* 4.12 Write property test for failed order descriptions
  - **Property 3: Failed orders store user-friendly descriptions**
  - **Validates: Requirements 1.5**

  - [x] 4.13 Write property test for terminal status clearing next_check_at
    - **Property 6: Terminal status transitions clear next check**
    - **Validates: Requirements 2.3, 7.3, 8.2, 9.2, 10.2**

- [x] 5. Create Celery configuration
  - Create coffee_payment/celery.py with Celery app configuration
  - Update coffee_payment/__init__.py to import Celery app
  - Configure Redis as message broker
  - Configure beat schedule for periodic task
  - _Requirements: 3.1_

- [x] 6. Create background check task
  - Create payments/tasks.py
  - Implement check_pending_payments() Celery task
  - Query Orders with status='pending', next_check_at <= now, expires_at > now
  - Sort by payment_started_at descending (newest first)
  - Increment check_attempts for each order
  - Update last_check_at for each order
  - Log count of pending orders found
  - Call PaymentStatusService for each order
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ]* 6.1 Write property test for query filtering
  - **Property 7: Background task queries correct pending orders**
  - **Validates: Requirements 3.1**

- [ ]* 6.2 Write property test for query sorting
  - **Property 8: Background task sorts by newest first**
  - **Validates: Requirements 3.2**

- [ ]* 6.3 Write property test for check_attempts increment
  - **Property 9: Check attempts increment on each check**
  - **Validates: Requirements 3.3**

- [x] 7. Update initiate_payment() to set payment_started_at
  - Modify initiate_payment() in views.py
  - Set payment_started_at to current timezone-aware timestamp when redirecting to payment provider
  - Set next_check_at to current time + FAST_TRACK_INTERVAL_S
  - _Requirements: 1.2, 1.3_

- [x] 8. Refactor webhook handler to use PaymentStatusService
  - Update yookassa_payment_result_webhook() in views.py
  - Extract payment status from webhook payload
  - Call PaymentStatusService.process_payment_status()
  - Remove duplicate status handling logic
  - Ensure time-based logic is applied (fast/slow track)
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ]* 8.1 Write property test for webhook fast track success
  - **Property 20: Webhook fast track success triggers drink preparation**
  - **Validates: Requirements 11.1**

- [ ]* 8.2 Write property test for webhook slow track success
  - **Property 21: Webhook slow track success triggers manual make**
  - **Validates: Requirements 11.2**

- [ ]* 8.3 Write property test for webhook canceled
  - **Property 22: Webhook canceled transitions to not paid**
  - **Validates: Requirements 11.3**

- [ ]* 8.4 Write property test for webhook waiting_for_capture
  - **Property 23: Webhook waiting for capture transitions to failed**
  - **Validates: Requirements 11.4**

- [x] 9. Add manual_make status to order status page template
  - Update order_status_page.html template
  - Add display logic for manual_make status
  - Add appropriate icon and message for manual_make
  - Add client_info_manual_make field to Device model
  - _Requirements: 2.1_

- [ ]* 9.1 Write property test for manual_make no drink preparation
  - **Property 5: Manual make orders do not trigger drink preparation**
  - **Validates: Requirements 2.2, 8.3**

- [x] 10. Update user messages for new error scenarios
  - Add messages for payment check failures to user_messages.py
  - Add message for manual_make status
  - Add message for exhausted retry attempts
  - _Requirements: 1.5, 2.1, 5.3_

- [x] 11. Add database index for efficient querying
  - Create migration to add composite index on (status, next_check_at, expires_at)
  - _Requirements: 3.1_

- [x] 12. Write integration tests for complete workflows
  - Test complete background check cycle for pending order
  - Test fast track success flow (check → paid → TMetr command)
  - Test slow track success flow (check → manual_make)
  - Test retry logic with network errors
  - Test failure after exhausting retries
  - Test webhook processing with shared logic
  - Test multiple orders processed in single task run
  - _Requirements: All_

- [x] 13. Update requirements.txt with Celery dependencies
  - Add celery package
  - Add redis package
  - Add hypothesis package for property-based testing
  - _Requirements: 3.1_

- [x] 14. Update PROJECT.md documentation
  - Document new manual_make status
  - Document background payment checking system
  - Document Celery setup and configuration
  - Document new Order model fields
  - Update architecture diagrams
  - _Requirements: All_

- [x] 15. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
