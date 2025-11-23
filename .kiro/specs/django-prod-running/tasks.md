# Implementation Plan

- [x] 1. Add Gunicorn and Uvicorn dependencies
  - Add `gunicorn>=21.2.0` to requirements.txt
  - Add `uvicorn[standard]>=0.27.0` to requirements.txt
  - _Requirements: 4.1, 4.2_

- [ ]* 1.1 Write property test for Docker dependencies
  - **Property 7: Docker image contains required dependencies**
  - **Validates: Requirements 4.1, 4.2**

- [x] 2. Create Gunicorn configuration file
  - Create `coffee_payment/gunicorn.conf.py`
  - Read environment variables with defaults (GUNICORN_WORKERS=4, GUNICORN_PORT=8000, GUNICORN_TIMEOUT=30, GUNICORN_MAX_REQUESTS=0, GUNICORN_MAX_REQUESTS_JITTER=0)
  - Configure worker_class as 'uvicorn.workers.UvicornWorker'
  - Configure bind address from GUNICORN_PORT
  - Configure timeout and graceful_timeout from GUNICORN_TIMEOUT
  - Configure max_requests and max_requests_jitter
  - Configure logging to stdout/stderr
  - Set wsgi_app to 'coffee_payment.asgi:application'
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11_

- [ ]* 2.1 Write property test for configuration through environment variables
  - **Property 4: Configuration through environment variables**
  - **Validates: Requirements 1.5, 2.1, 2.2, 2.3, 2.4, 2.5**

- [ ]* 2.2 Write property test for default configuration values
  - **Property 5: Default configuration values**
  - **Validates: Requirements 2.6, 2.7, 2.8, 2.9, 2.10, 2.11**

- [ ]* 2.3 Write unit tests for gunicorn.conf.py
  - Test configuration file loads without errors
  - Test default values are applied when ENV vars not set
  - Test custom values are applied when ENV vars are set
  - Test invalid values fall back to defaults
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 3. Update entrypoint.sh to support production mode
  - Keep existing migration and superuser creation logic
  - Add check for RUN_MODE environment variable
  - If RUN_MODE=development, use `python manage.py runserver 0.0.0.0:8000`
  - If RUN_MODE is not set or equals production, use `gunicorn -c gunicorn.conf.py coffee_payment.asgi:application`
  - Add logging to indicate which mode is starting
  - _Requirements: 4.6_

- [ ]* 3.1 Write property test for entrypoint mode support
  - **Property 11: Entrypoint supports multiple modes**
  - **Validates: Requirements 4.6**

- [ ]* 3.2 Write unit tests for entrypoint script
  - Test development mode detection and command
  - Test production mode detection and command
  - Test default mode (production) when RUN_MODE not set
  - _Requirements: 4.6_

- [x] 4. Update Dockerfile for production deployment
  - Keep existing base image and system dependencies
  - Keep existing WORKDIR, COPY, and pip install steps
  - Keep existing entrypoint.sh setup
  - Change EXPOSE to use GUNICORN_PORT with default 8000
  - Update CMD to use entrypoint.sh without explicit command (will default to production mode)
  - Ensure ENV variables can be passed to container
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ]* 4.1 Write property test for container command
  - **Property 8: Container starts with correct command**
  - **Validates: Requirements 4.3**

- [ ]* 4.2 Write property test for container environment configuration
  - **Property 9: Container supports environment configuration**
  - **Validates: Requirements 4.4**

- [ ]* 4.3 Write property test for container port exposure
  - **Property 10: Container exposes configured port**
  - **Validates: Requirements 4.5**

- [x] 5. Update docker-compose.yml for development
  - Add RUN_MODE=development to environment variables for web service
  - Keep existing service configuration
  - Ensure development mode uses runserver
  - _Requirements: 4.6_

- [x] 6. Checkpoint - Test Gunicorn startup locally
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 6.1 Write integration test for Gunicorn startup
  - Test application starts with Gunicorn
  - Test multiple workers are spawned
  - Test health check endpoint responds correctly
  - _Requirements: 1.1, 1.2, 2.1, 6.1_

- [ ]* 6.2 Write property test for Gunicorn process
  - **Property 1: Gunicorn process is the main process manager**
  - **Validates: Requirements 1.1, 1.2**

- [ ]* 6.3 Write property test for ASGI application
  - **Property 2: ASGI application is correctly configured**
  - **Validates: Requirements 1.3**

- [ ]* 6.4 Write property test for request distribution
  - **Property 3: Requests are distributed across workers**
  - **Validates: Requirements 1.4**

- [x] 7. Add environment variables documentation to README.md
  - Add new section or extend existing environment variables table
  - Document GUNICORN_WORKERS (Number of Gunicorn worker processes, default: 4)
  - Document GUNICORN_PORT (Port for Gunicorn to bind to, default: 8000)
  - Document GUNICORN_TIMEOUT (Request timeout in seconds, default: 30)
  - Document GUNICORN_MAX_REQUESTS (Requests before worker restart, default: 0 - unlimited)
  - Document GUNICORN_MAX_REQUESTS_JITTER (Random jitter for worker restart, default: 0)
  - Document RUN_MODE (Server mode: development or production, default: production)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 8. Update PROJECT.md documentation
  - Add section "Production Deployment with Gunicorn + Uvicorn"
  - Describe the two-tier architecture (Gunicorn master + Uvicorn workers)
  - Explain worker count calculation: (2 * CPU_cores) + 1
  - Document graceful shutdown behavior with SIGTERM/SIGINT
  - Add Kubernetes deployment considerations (terminationGracePeriodSeconds, resource limits)
  - Reference environment variables table in README.md
  - Add monitoring recommendations (worker count, restarts, latency, memory)
  - _Requirements: 5.7, 5.8, 5.9, 5.10_

- [ ]* 9. Write integration test for graceful shutdown
  - **Property 6: Graceful shutdown on signals**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

- [ ]* 9.1 Write integration tests for shutdown behavior
  - Test SIGTERM triggers graceful shutdown
  - Test SIGINT triggers graceful shutdown
  - Test active requests complete before shutdown
  - Test new requests are rejected during shutdown
  - Test shutdown completes within timeout
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.7_

- [ ]* 10. Write integration test for health check with Gunicorn
  - **Property 12: Health check works with Gunicorn**
  - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [ ]* 10.1 Write integration tests for health check
  - Test health check endpoint is accessible with Gunicorn
  - Test health check works with multiple workers
  - Test health check works during worker restarts
  - Test readiness probe succeeds
  - Test liveness probe succeeds
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 11. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

