# Implementation Plan

- [x] 1. Implement health check endpoint
  - Create simple view function that returns JSON response with status and timestamp
  - Add URL route at `/health`
  - Ensure no database queries or external API calls are made
  - Return 200 OK for normal operation, 500 for errors
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [ ]* 1.1 Write property test for health check response time
  - **Property 1: Health check response time**
  - **Validates: Requirements 1.1**

- [ ]* 1.2 Write property test for health check independence
  - **Property 2: Health check has no external dependencies**
  - **Validates: Requirements 1.4, 1.5**

- [ ]* 1.3 Write unit tests for health check endpoint
  - Test successful response format (200 OK with JSON)
  - Test error response (500 status code)
  - Test endpoint accessibility at `/health`
  - _Requirements: 1.2, 1.3, 1.6_

- [x] 2. Add PostgreSQL SSL support
  - Add new environment variables for SSL configuration (POSTGRES_SSL_MODE, POSTGRES_SSL_CERT, POSTGRES_SSL_KEY, POSTGRES_SSL_ROOT_CERT)
  - Extend database configuration in settings.py to include SSL options when environment variables are set
  - Add logging for SSL configuration status on startup
  - Ensure SSL is disabled by default for local development
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [ ]* 2.1 Write property test for SSL configuration application
  - **Property 4: SSL configuration is applied when provided**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

- [ ]* 2.2 Write unit tests for SSL configuration
  - Test SSL configuration is applied when environment variables are set
  - Test SSL configuration is not applied in local development (default)
  - Test various SSL modes (require, verify-ca, verify-full)
  - Test certificate file paths are correctly passed to database config
  - Test error logging for invalid SSL configuration
  - _Requirements: 3.1, 3.2, 3.3, 3.9, 3.10_

- [x] 3. Create environment variables documentation table in README.md
  - Create comprehensive table with columns: Variable Name, Description, Default Value
  - Document all Django core variables (SECRET_KEY, DEBUG, ALLOWED_HOSTS, BASE_URL, etc.)
  - Document all database configuration variables (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
  - Document all PostgreSQL SSL variables (POSTGRES_SSL_MODE, POSTGRES_SSL_CERT, POSTGRES_SSL_KEY, POSTGRES_SSL_ROOT_CERT)
  - Document all TMetr API variables (TMETR_TOKEN, TMETR_HOST)
  - Document all payment provider variables (Yookassa, TBank credentials)
  - Document all Celery variables (CELERY_BROKER_URL, CELERY_RESULT_BACKEND)
  - Document all application settings (ORDER_EXPIRATION_MINUTES, DEVICE_ONLINE_THRESHOLD_MINUTES, PAYMENT_SCENARIOS, DEFAULT_PAYMENT_SCENARIO)
  - Document all background payment check variables (PAYMENT_CHECK_INTERVAL_S, FAST_TRACK_LIMIT_S, FAST_TRACK_INTERVAL_S, SLOW_TRACK_INTERVAL_S, PAYMENT_ATTEMPTS_LIMIT, PAYMENT_API_TIMEOUT_S)
  - Document all logging configuration variables
  - Use "—" for variables without default values
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

- [ ]* 3.1 Write property test for environment variable documentation completeness
  - **Property 3: Environment variable documentation completeness**
  - **Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9**

- [ ]* 3.2 Write unit test for documentation table structure
  - Test table has required columns (Variable Name, Description, Default Value)
  - Test "—" is used for variables without defaults
  - _Requirements: 2.2, 2.10_

- [x] 4. Squash Django migrations
  - Run `python manage.py squashmigrations payments 0001 0026` to squash all migrations
  - Review squashed migration file to ensure all operations are preserved
  - Test squashed migrations on a clean test database
  - Verify all model fields, indexes, and constraints are created correctly
  - Run full test suite to ensure functionality is preserved
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 4.1 Write property test for squashed migration equivalence
  - **Property 5: Squashed migrations produce equivalent schema**
  - **Validates: Requirements 4.1, 4.3**

- [ ]* 4.2 Write integration test for squashed migrations
  - Test squashed migrations create correct schema on clean database
  - Test all model fields are present after squashed migrations
  - Test all indexes are created correctly
  - Test all constraints are applied
  - Verify migration count is reduced
  - _Requirements: 4.1, 4.3, 4.4_

- [x] 5. Update PROJECT.md documentation
  - Add section describing the health check endpoint and its usage
  - Add reference to environment variables table in README.md
  - Add section describing PostgreSQL SSL configuration
  - Add section describing migration squashing process
  - Ensure all updates follow CONSTITUTION.md principles
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
