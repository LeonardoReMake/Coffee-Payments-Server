# Design Document

## Overview

This design document outlines the technical approach for configuring the Coffee Payments Server to run in production using Gunicorn with Uvicorn workers. The implementation focuses on:

1. **Production Server Setup** - Gunicorn as process manager with Uvicorn ASGI workers
2. **Environment-Based Configuration** - Flexible configuration through ENV variables
3. **Graceful Shutdown** - Proper signal handling for Kubernetes orchestration
4. **Docker Integration** - Production-ready containerization
5. **Documentation Updates** - Comprehensive deployment documentation

The design follows MVP principles from CONSTITUTION.md, using proven production patterns and avoiding unnecessary complexity.

## Architecture

### Production Server Stack

The application will use a two-tier server architecture:

**Tier 1: Gunicorn (Process Manager)**
- Manages multiple worker processes
- Handles load balancing across workers
- Monitors worker health and restarts failed workers
- Handles graceful shutdown signals (SIGTERM, SIGINT)

**Tier 2: Uvicorn Workers (ASGI Server)**
- Each worker runs Uvicorn ASGI server
- Handles async Django requests
- Supports WebSocket connections (if needed in future)
- Efficient handling of concurrent requests

**Architecture Diagram:**
```
Kubernetes Pod
  └─> Container
       └─> Gunicorn (Master Process)
            ├─> UvicornWorker 1 (ASGI)
            ├─> UvicornWorker 2 (ASGI)
            ├─> UvicornWorker 3 (ASGI)
            └─> UvicornWorker 4 (ASGI)
```

### Configuration Strategy

All Gunicorn parameters will be configurable through environment variables with sensible defaults:

| ENV Variable | Purpose | Default |
|-------------|---------|---------|
| GUNICORN_WORKERS | Number of worker processes | 4 |
| GUNICORN_PORT | Bind port | 8000 |
| GUNICORN_TIMEOUT | Request timeout (seconds) | 30 |
| GUNICORN_MAX_REQUESTS | Requests before worker restart | 0 (unlimited) |
| GUNICORN_MAX_REQUESTS_JITTER | Random jitter for restart | 0 |

**Worker Count Calculation:**
- Default: 4 workers (suitable for most deployments)
- Recommended formula: `(2 * CPU_cores) + 1`
- Can be adjusted based on workload characteristics

**Timeout Configuration:**
- Default: 30 seconds (covers most payment API calls)
- Should be higher than longest expected API call (Tmetr, Yookassa, TBank)
- Kubernetes should have longer termination grace period

**Max Requests Configuration:**
- Default: 0 (unlimited, workers never restart)
- Production recommendation: 1000-5000 (prevents memory leaks)
- Jitter prevents all workers restarting simultaneously

### Graceful Shutdown

Gunicorn natively supports graceful shutdown through signal handling:

**Shutdown Flow:**
1. Kubernetes sends SIGTERM to container
2. Gunicorn master process receives SIGTERM
3. Gunicorn stops accepting new connections
4. Gunicorn waits for active requests to complete (up to timeout)
5. Gunicorn sends SIGTERM to all workers
6. Workers finish current requests and exit
7. Master process exits

**No Code Changes Required:**
- Django ASGI application already supports graceful shutdown
- Gunicorn handles all signal management
- No custom signal handlers needed

**Kubernetes Configuration:**
```yaml
terminationGracePeriodSeconds: 60  # Should be > GUNICORN_TIMEOUT
```

## Components and Interfaces

### Gunicorn Configuration

**Implementation Approach:**
- Create `gunicorn.conf.py` configuration file
- Read environment variables with defaults
- Configure worker class, bind address, timeouts

**Configuration File Location:** `coffee_payment/gunicorn.conf.py`

**Configuration Structure:**
```python
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('GUNICORN_PORT', '8000')}"

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', '4'))
worker_class = 'uvicorn.workers.UvicornWorker'

# Timeouts
timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))
graceful_timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))

# Worker lifecycle
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '0'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '0'))

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'

# Application
wsgi_app = 'coffee_payment.asgi:application'
```

### Dockerfile Updates

**Current State:**
- Uses `python manage.py runserver` (development server)
- Not suitable for production

**Required Changes:**
1. Install Gunicorn and Uvicorn in requirements.txt
2. Update CMD to use Gunicorn
3. Support both development and production modes

**Updated Dockerfile CMD:**
```dockerfile
# Production mode (default)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "coffee_payment.asgi:application"]
```

**Development Mode Override:**
```bash
docker run -e RUN_MODE=development app
# entrypoint.sh will detect RUN_MODE and use runserver
```

### Entrypoint Script Updates

**Current State:**
- Runs migrations
- Creates superuser
- Executes CMD

**Required Changes:**
- Add support for development vs production mode
- Keep existing migration and superuser logic

**Updated entrypoint.sh:**
```bash
#!/bin/sh

# Apply migrations
python manage.py migrate

# Create superuser if credentials provided
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ] && [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser --no-input || true
fi

# Check run mode
if [ "$RUN_MODE" = "development" ]; then
    echo "Starting in development mode..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting in production mode with Gunicorn..."
    exec gunicorn -c gunicorn.conf.py coffee_payment.asgi:application
fi
```

### Dependencies

**New Dependencies to Add:**
- `gunicorn>=21.2.0` - ASGI-capable version
- `uvicorn[standard]>=0.27.0` - ASGI server with performance extras

**Standard extras include:**
- `uvloop` - Fast event loop (Linux/macOS)
- `httptools` - Fast HTTP parser
- `websockets` - WebSocket support

## Data Models

No new data models are required. This feature only affects deployment configuration.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Gunicorn process is the main process manager

*For any* production deployment, the main process should be Gunicorn with UvicornWorker class for ASGI support
**Validates: Requirements 1.1, 1.2**

### Property 2: ASGI application is correctly configured

*For any* application start, the Django ASGI application at `coffee_payment.asgi:application` should load successfully and be callable
**Validates: Requirements 1.3**

### Property 3: Requests are distributed across workers

*For any* set of concurrent HTTP requests, Gunicorn should distribute them across multiple worker processes
**Validates: Requirements 1.4**

### Property 4: Configuration through environment variables

*For any* valid environment variable (GUNICORN_WORKERS, GUNICORN_PORT, GUNICORN_TIMEOUT, GUNICORN_MAX_REQUESTS, GUNICORN_MAX_REQUESTS_JITTER), the system should apply that configuration value
**Validates: Requirements 1.5, 2.1, 2.2, 2.3, 2.4, 2.5**

### Property 5: Default configuration values

*For any* missing environment variable, the system should use the documented default value (workers=4, port=8000, timeout=30, max_requests=0, jitter=0)
**Validates: Requirements 2.6, 2.7, 2.8, 2.9, 2.10, 2.11**

### Property 6: Graceful shutdown on signals

*For any* shutdown signal (SIGTERM or SIGINT), Gunicorn should initiate graceful shutdown, stop accepting new requests, complete active requests, and terminate workers cleanly within the timeout period
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

### Property 7: Docker image contains required dependencies

*For any* built Docker image, Gunicorn and Uvicorn with standard extras should be installed and available
**Validates: Requirements 4.1, 4.2**

### Property 8: Container starts with correct command

*For any* container start in production mode, the entrypoint should execute Gunicorn with UvicornWorker and the ASGI application
**Validates: Requirements 4.3**

### Property 9: Container supports environment configuration

*For any* environment variable passed to the container, it should be available to the application and affect its configuration
**Validates: Requirements 4.4**

### Property 10: Container exposes configured port

*For any* configured GUNICORN_PORT value, the Docker container should expose that port
**Validates: Requirements 4.5**

### Property 11: Entrypoint supports multiple modes

*For any* RUN_MODE setting (development or production), the entrypoint should start the appropriate server (runserver for development, Gunicorn for production)
**Validates: Requirements 4.6**

### Property 12: Health check works with Gunicorn

*For any* Gunicorn configuration (number of workers, worker restarts), the health check endpoint should remain accessible and respond successfully to readiness and liveness probes
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

## Error Handling

### Configuration Errors

**Invalid Environment Variables:**
- Invalid worker count (non-numeric, negative) → Use default value (4)
- Invalid port (non-numeric, out of range) → Use default value (8000)
- Invalid timeout (non-numeric, negative) → Use default value (30)
- Log warning for invalid values

**Missing Dependencies:**
- Gunicorn not installed → Container build fails (fail fast)
- Uvicorn not installed → Container build fails (fail fast)

### Runtime Errors

**Worker Failures:**
- Worker crashes → Gunicorn automatically restarts worker
- Worker hangs → Gunicorn kills worker after timeout and restarts
- All workers fail → Gunicorn master process exits (Kubernetes restarts pod)

**Port Binding Errors:**
- Port already in use → Gunicorn fails to start (logged to stderr)
- Permission denied (port < 1024) → Gunicorn fails to start

**Graceful Shutdown Errors:**
- Requests exceed timeout → Gunicorn forcefully terminates workers
- Worker doesn't respond to SIGTERM → Gunicorn sends SIGKILL after grace period

### Logging

All errors will be logged to stderr for Kubernetes log collection:
- Worker lifecycle events (start, restart, stop)
- Configuration values on startup
- Graceful shutdown progress
- Request timeout warnings

## Testing Strategy

### Unit Tests

**Configuration Tests:**
- Test default values are applied when ENV variables not set
- Test custom values are applied when ENV variables are set
- Test invalid values fall back to defaults
- Test gunicorn.conf.py loads correctly

**Entrypoint Tests:**
- Test development mode detection
- Test production mode detection
- Test migration execution
- Test superuser creation

### Integration Tests

**Gunicorn Integration:**
- Test application starts with Gunicorn
- Test multiple workers are spawned
- Test health check endpoint responds correctly
- Test requests are distributed across workers
- Test worker restart after max_requests

**Graceful Shutdown Integration:**
- Test SIGTERM triggers graceful shutdown
- Test active requests complete before shutdown
- Test new requests are rejected during shutdown
- Test shutdown completes within timeout

**Docker Integration:**
- Test container builds successfully
- Test container starts with Gunicorn
- Test environment variables are passed correctly
- Test health check works in container
- Test logs are captured correctly

### Load Testing

**Performance Validation:**
- Test application handles concurrent requests
- Test worker load balancing
- Test memory usage over time
- Test worker restart doesn't drop requests
- Compare performance with development server

### Manual Testing

**Kubernetes Deployment:**
- Deploy to staging environment
- Verify pod starts successfully
- Verify readiness probe succeeds
- Verify liveness probe succeeds
- Test rolling update (graceful shutdown)
- Test pod termination (no dropped requests)

## Deployment Considerations

### Development Environment

**Local Development:**
- Continue using `python manage.py runserver`
- Set `RUN_MODE=development` in docker-compose.yml
- No Gunicorn overhead for development

**Docker Compose:**
```yaml
services:
  web:
    environment:
      - RUN_MODE=development
```

### Staging Environment

**Configuration:**
- Use Gunicorn with 2-4 workers
- Set reasonable timeout (30s)
- Enable max_requests for memory leak protection
- Monitor worker restarts

**Kubernetes Manifest:**
```yaml
env:
  - name: GUNICORN_WORKERS
    value: "2"
  - name: GUNICORN_TIMEOUT
    value: "30"
  - name: GUNICORN_MAX_REQUESTS
    value: "1000"
  - name: GUNICORN_MAX_REQUESTS_JITTER
    value: "100"
```

### Production Environment

**Configuration:**
- Calculate workers based on CPU cores: `(2 * cores) + 1`
- Set timeout higher than longest API call (suggest 60s)
- Enable max_requests (suggest 5000)
- Add jitter to prevent thundering herd (suggest 500)

**Resource Limits:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

**Termination Grace Period:**
```yaml
terminationGracePeriodSeconds: 90  # > GUNICORN_TIMEOUT
```

### Monitoring

**Metrics to Track:**
- Worker count (should match GUNICORN_WORKERS)
- Worker restarts (should be periodic if max_requests set)
- Request latency (should be consistent across workers)
- Memory usage per worker (should be stable)
- Graceful shutdown duration (should be < timeout)

**Logging:**
- Gunicorn access logs (stdout)
- Gunicorn error logs (stderr)
- Django application logs (existing logging)

## Performance Considerations

### Worker Count Optimization

**Too Few Workers:**
- Underutilized CPU
- Higher request latency
- Lower throughput

**Too Many Workers:**
- Memory pressure
- Context switching overhead
- Database connection pool exhaustion

**Recommendation:**
- Start with `(2 * CPU_cores) + 1`
- Monitor CPU and memory usage
- Adjust based on workload characteristics

### Memory Management

**Worker Restart Strategy:**
- Set max_requests to prevent memory leaks
- Add jitter to prevent simultaneous restarts
- Monitor memory usage per worker

**Database Connections:**
- Each worker maintains its own connection pool
- Total connections = workers * pool_size
- Ensure database can handle total connections

### Request Timeout

**Considerations:**
- Should be higher than longest API call
- Tmetr API: typically < 5s
- Yookassa API: typically < 10s
- TBank API: typically < 10s
- Recommendation: 30-60s

**Timeout Too Low:**
- Legitimate requests killed
- User sees errors

**Timeout Too High:**
- Hung workers not detected
- Resources wasted on stuck requests

## Security Considerations

### Process Isolation

- Each worker runs in separate process
- Worker crash doesn't affect other workers
- Memory isolation between workers

### Signal Handling

- Only master process handles SIGTERM/SIGINT
- Workers cannot be directly signaled from outside
- Prevents accidental worker termination

### Port Binding

- Bind to 0.0.0.0 (all interfaces) for Kubernetes
- Port should be > 1024 (no root required)
- Default 8000 is safe

### Environment Variables

- Sensitive values should not have defaults
- Use Kubernetes secrets for sensitive data
- Log configuration values (except secrets) on startup

## Monitoring and Logging

### Gunicorn Logs

**Access Logs (stdout):**
- Request method, path, status code
- Response time
- Client IP (from Kubernetes ingress)

**Error Logs (stderr):**
- Worker lifecycle events
- Configuration errors
- Application exceptions
- Timeout warnings

### Application Logs

- Existing Django logging continues to work
- Each worker logs independently
- Logs aggregated by Kubernetes

### Health Monitoring

- Kubernetes readiness probe: `/health`
- Kubernetes liveness probe: `/health`
- Probe frequency: every 10s
- Probe timeout: 1s

## Future Enhancements

1. **Auto-scaling** - Horizontal pod autoscaling based on CPU/memory
2. **Worker Tuning** - Dynamic worker count based on load
3. **Metrics Endpoint** - Prometheus metrics for Gunicorn
4. **Request Tracing** - Distributed tracing across workers
5. **Connection Pooling** - Optimize database connections per worker
6. **WebSocket Support** - Enable WebSocket for real-time features

