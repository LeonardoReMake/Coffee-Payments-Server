# Design Document

## Overview

This design document outlines the technical approach for preparing the Coffee Payments Server for production deployment. The implementation focuses on four key areas:

1. **Health Check Endpoint** - Lightweight HTTP endpoint for Kubernetes monitoring
2. **Environment Variables Documentation** - Comprehensive table of all configuration options
3. **PostgreSQL SSL Support** - Secure database connections for production environment
4. **Migration Optimization** - Squashing migrations for efficient deployment

The design follows MVP principles from CONSTITUTION.md, prioritizing simplicity and using proven Django patterns.

## Architecture

### Health Check Endpoint

The health check will be implemented as a simple Django view that returns a JSON response. It will not depend on external services or database queries to ensure fast response times.

**Endpoint:** `/health`

**Response Format:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T10:30:00+00:00"
}
```

**Implementation Approach:**
- Simple function-based view in `payments/views.py`
- No database queries or external API calls
- Returns 200 OK when application is running
- Returns 500 if critical application errors are detected
- Response time target: < 100ms

### Environment Variables Documentation

A comprehensive table will be added to README.md documenting all environment variables used by the application.

**Table Structure:**
| Variable Name | Description | Default Value |
|--------------|-------------|---------------|

**Categories to Document:**
1. Django Core (SECRET_KEY, DEBUG, ALLOWED_HOSTS, etc.)
2. Database Configuration (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
3. PostgreSQL SSL (POSTGRES_SSL_CERT, POSTGRES_SSL_KEY, POSTGRES_SSL_ROOT_CERT, POSTGRES_SSL_MODE)
4. TMetr API (TMETR_TOKEN, TMETR_HOST)
5. Payment Providers (Yookassa, TBank credentials)
6. Celery (CELERY_BROKER_URL, CELERY_RESULT_BACKEND)
7. Application Settings (ORDER_EXPIRATION_MINUTES, DEVICE_ONLINE_THRESHOLD_MINUTES)
8. Background Payment Check (PAYMENT_CHECK_INTERVAL_S, FAST_TRACK_LIMIT_S, etc.)
9. Logging Configuration

### PostgreSQL SSL Configuration

SSL support will be added to the database configuration in `settings.py` using Django's built-in SSL options for PostgreSQL.

**New Environment Variables:**
- `POSTGRES_SSL_MODE` - SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
- `POSTGRES_SSL_CERT` - Path to client certificate file
- `POSTGRES_SSL_KEY` - Path to client key file
- `POSTGRES_SSL_ROOT_CERT` - Path to root certificate file

**Implementation Approach:**
- Extend the existing database configuration in `settings.py`
- Add SSL options to the PostgreSQL database configuration
- Default to no SSL for local development (when DB_NAME is not set)
- Enable SSL when SSL environment variables are present
- Log SSL configuration status on startup

**Django Database Configuration:**
```python
if os.getenv('DB_NAME'):
    db_config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
    
    # Add SSL configuration if provided
    ssl_mode = os.getenv('POSTGRES_SSL_MODE')
    if ssl_mode:
        db_config['OPTIONS'] = {'sslmode': ssl_mode}
        
        ssl_cert = os.getenv('POSTGRES_SSL_CERT')
        ssl_key = os.getenv('POSTGRES_SSL_KEY')
        ssl_root_cert = os.getenv('POSTGRES_SSL_ROOT_CERT')
        
        if ssl_cert:
            db_config['OPTIONS']['sslcert'] = ssl_cert
        if ssl_key:
            db_config['OPTIONS']['sslkey'] = ssl_key
        if ssl_root_cert:
            db_config['OPTIONS']['sslrootcert'] = ssl_root_cert
    
    DATABASES = {'default': db_config}
```

### Migration Squashing

Django migrations will be squashed to reduce the number of migration files and improve deployment efficiency.

**Approach:**
1. Use Django's `squashmigrations` management command
2. Squash migrations in the `payments` app
3. Test squashed migrations on a clean database
4. Verify all schema operations are preserved
5. Update migration dependencies

**Command:**
```bash
python manage.py squashmigrations payments 0001 0026
```

**Verification Steps:**
1. Create a fresh test database
2. Apply squashed migrations
3. Compare schema with production database
4. Run all tests to ensure functionality is preserved

## Components and Interfaces

### Health Check View

**Function:** `health_check(request)`

**Location:** `coffee_payment/payments/views.py`

**Input:** HTTP GET request

**Output:** JSON response with status and timestamp

**Error Handling:** Returns 500 status code if application is in error state

### Environment Variables Table

**Location:** `README.md`

**Format:** Markdown table

**Content:** All environment variables with descriptions and defaults

### SSL Configuration

**Location:** `coffee_payment/coffee_payment/settings.py`

**Components:**
- Environment variable reading
- SSL options dictionary construction
- Database configuration with SSL

**Integration Points:**
- Django database connection
- Celery worker database connections (inherits from Django settings)

### Migration Squashing

**Tool:** Django management command `squashmigrations`

**Target:** `payments` app migrations (0001 through 0026)

**Output:** New squashed migration file

## Data Models

No new data models are required for this feature. All changes are configuration and infrastructure-related.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Health check response time

*For any* health check request, the response time should be less than 100 milliseconds
**Validates: Requirements 1.1**

### Property 2: Health check has no external dependencies

*For any* health check request, no external service calls or database queries should be made during execution
**Validates: Requirements 1.4, 1.5**

### Property 3: Environment variable documentation completeness

*For any* environment variable referenced in settings.py using `os.getenv()`, that variable should appear in the README.md environment variables table
**Validates: Requirements 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9**

### Property 4: SSL configuration is applied when provided

*For any* database configuration when SSL environment variables (POSTGRES_SSL_MODE, POSTGRES_SSL_CERT, POSTGRES_SSL_KEY, POSTGRES_SSL_ROOT_CERT) are set, the database OPTIONS dictionary should contain the corresponding SSL parameters
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

### Property 5: Squashed migrations produce equivalent schema

*For any* clean database, applying squashed migrations should produce a schema that is equivalent to applying the original migrations (same tables, columns, indexes, and constraints)
**Validates: Requirements 4.1, 4.3**

## Error Handling

### Health Check Errors

- **Application Error State:** Return HTTP 500 with error status in JSON
- **Unexpected Exceptions:** Catch all exceptions and return 500 status
- **Logging:** Log all health check failures for debugging

### SSL Configuration Errors

- **Missing Certificate Files:** Log detailed error message with file path
- **Invalid SSL Mode:** Log warning and fall back to no SSL
- **Connection Failures:** Django will raise standard database connection errors
- **Logging:** Log SSL configuration on startup (enabled/disabled, mode)

### Migration Squashing Errors

- **Dependency Conflicts:** Manually resolve before squashing
- **Schema Mismatch:** Abort squashing and investigate differences
- **Test Failures:** Do not deploy squashed migrations until all tests pass

## Testing Strategy

### Unit Tests

**Health Check Tests:**
- Test successful health check response (200 OK)
- Test response format (JSON with status and timestamp)
- Test response time (< 100ms)
- Test that no database queries are made
- Test that no external API calls are made

**SSL Configuration Tests:**
- Test SSL configuration is applied when environment variables are set
- Test SSL configuration is not applied in local development
- Test various SSL modes (require, verify-ca, verify-full)
- Test certificate file paths are correctly passed to database config

**Migration Tests:**
- Test squashed migrations create correct schema on clean database
- Test all model fields are present after squashed migrations
- Test all indexes are created correctly
- Test all constraints are applied

### Integration Tests

**Health Check Integration:**
- Test health check endpoint is accessible at `/health`
- Test Kubernetes can successfully call health check
- Test health check works in Docker container

**SSL Integration:**
- Test database connection with SSL in production-like environment
- Test Celery workers can connect to database with SSL
- Test SSL certificate validation

**Migration Integration:**
- Test squashed migrations work with existing data
- Test rollback scenarios
- Test migration on production-like database

### Manual Testing

**Environment Variables Documentation:**
- Manually review README.md table for completeness
- Verify all variables in settings.py are documented
- Verify default values are accurate
- Test configuration with documented variables

**Migration Squashing:**
- Deploy squashed migrations to staging environment
- Verify application functionality
- Compare database schema with production
- Run full test suite

## Deployment Considerations

### Health Check Deployment

1. Deploy health check endpoint
2. Configure Kubernetes readiness probe: `GET /health`
3. Configure Kubernetes liveness probe: `GET /health`
4. Set probe timeout to 1 second
5. Set probe period to 10 seconds

### SSL Configuration Deployment

1. Obtain SSL certificates from database administrator
2. Store certificates securely (Kubernetes secrets or secure file storage)
3. Set environment variables in deployment configuration
4. Test database connection before full deployment
5. Monitor connection logs for SSL errors

### Migration Squashing Deployment

1. Test squashed migrations in staging environment
2. Backup production database before deployment
3. Apply squashed migrations during maintenance window
4. Verify application functionality after deployment
5. Monitor for any migration-related errors

### Documentation Deployment

1. Update README.md with environment variables table
2. Update PROJECT.md with production preparation information
3. Commit documentation changes
4. Ensure documentation is accessible to DevOps team

## Performance Considerations

### Health Check Performance

- Target response time: < 100ms
- No database queries or external API calls
- Minimal CPU and memory usage
- Can handle high request rates from Kubernetes probes

### SSL Performance

- SSL adds minimal overhead to database connections
- Connection pooling mitigates SSL handshake overhead
- No impact on application response times

### Migration Performance

- Squashed migrations reduce migration time on clean databases
- No impact on existing databases (migrations already applied)
- Faster deployment to new environments

## Security Considerations

### Health Check Security

- Health check endpoint does not expose sensitive information
- No authentication required (public endpoint for Kubernetes)
- Does not reveal application internals or configuration

### SSL Security

- SSL certificates must be stored securely
- Certificate files should have restricted file permissions (600)
- SSL mode should be set to `require` or higher in production
- Root certificate should be used to verify server identity

### Environment Variables Security

- Sensitive values (SECRET_KEY, API keys) should not have defaults in documentation
- Production values should be stored in secure configuration management
- Documentation should note which variables contain sensitive data

## Monitoring and Logging

### Health Check Monitoring

- Monitor health check response times
- Alert on health check failures
- Track health check success rate

### SSL Monitoring

- Log SSL configuration on application startup
- Monitor database connection errors
- Alert on SSL certificate expiration

### Migration Monitoring

- Log migration execution time
- Monitor for migration failures
- Track migration history

## Future Enhancements

1. **Enhanced Health Checks** - Add optional deep health checks that verify database and external service connectivity
2. **Health Check Metrics** - Expose Prometheus metrics from health check endpoint
3. **SSL Certificate Rotation** - Automate SSL certificate renewal and rotation
4. **Migration Automation** - Automate migration squashing as part of CI/CD pipeline
5. **Configuration Validation** - Add startup validation for all environment variables
