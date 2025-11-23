# Design Document

## Overview

Данный документ описывает дизайн рефакторинга системы логирования в проекте Coffee Payments Server. Цель рефакторинга — привести систему логирования в соответствие с best practices для контейнеризированных приложений и обеспечить совместимость с современными системами лог-агрегации (Loki, ELK, CloudWatch).

**Ключевые изменения:**
- Переход от файлового логирования к stdout/stderr
- Унификация формата логов в JSON
- Централизованное управление уровнем логирования через переменную окружения LOG_LEVEL
- Упрощение Docker образа за счет удаления директорий для логов

## Architecture

### Current Architecture

**Текущая система логирования:**
```
Django Application
    ↓
LOGGING Configuration (settings.py)
    ↓
File Handler (logs/coffee_payment.log)
    ↓
JSON Formatter
    ↓
Log File on Disk
```

**Проблемы текущей архитектуры:**
1. Логи записываются в файл, что несовместимо с Kubernetes best practices
2. Каждый логгер настраивается отдельно с явным указанием handler
3. Уровень логирования жестко закодирован (DEBUG) для каждого логгера
4. Docker контейнер создает директорию для логов, которая не используется в продовом окружении
5. Нет централизованного управления уровнем логирования

### Target Architecture

**Новая система логирования:**
```
Django Application / Celery
    ↓
LOGGING Configuration (settings.py)
    ↓
Root Logger (level from LOG_LEVEL env)
    ↓
Console Handler (StreamHandler)
    ↓
JSON Formatter
    ↓
stdout (INFO, DEBUG, WARNING) / stderr (ERROR, CRITICAL)
    ↓
Kubernetes Log Collector
    ↓
Log Aggregation System (Loki/ELK/CloudWatch)
```

**Преимущества новой архитектуры:**
1. Совместимость с Kubernetes и контейнерными окружениями
2. Централизованное управление уровнем логирования через LOG_LEVEL
3. Упрощенная конфигурация — все логгеры наследуют настройки от root logger
4. Единый JSON формат для всех логов
5. Автоматическая маршрутизация логов в stdout/stderr по уровню
6. Упрощенный Docker образ без директорий для логов

## Components and Interfaces

### 1. Django LOGGING Configuration

**Расположение:** `coffee_payment/coffee_payment/settings.py`

**Компоненты:**

#### 1.1 Formatters

```python
'formatters': {
    'json': {
        'format': '{"timestamp": "%(asctime)s", "tag": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
    },
}
```

**Описание:** JSON formatter остается без изменений, используется для всех логов.

#### 1.2 Handlers

```python
'handlers': {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'json',
        'stream': 'ext://sys.stdout',  # По умолчанию stdout
    },
}
```

**Изменения:**
- Удален `file` handler
- Добавлен `console` handler с использованием `StreamHandler`
- По умолчанию вывод в stdout
- Логи уровня ERROR и CRITICAL автоматически перенаправляются в stderr через стандартное поведение Python logging

#### 1.3 Root Logger

```python
'root': {
    'handlers': ['console'],
    'level': os.getenv('LOG_LEVEL', 'INFO'),
}
```

**Описание:**
- Root logger использует console handler
- Уровень логирования читается из переменной окружения LOG_LEVEL
- Значение по умолчанию: INFO
- Все child логгеры наследуют эту конфигурацию

#### 1.4 Specific Loggers

```python
'loggers': {
    'django': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'propagate': False,
    },
    # Другие специфичные логгеры при необходимости
}
```

**Изменения:**
- Все специфичные логгеры используют console handler
- Уровень логирования читается из LOG_LEVEL
- Удалены все явные ссылки на file handler

### 2. LOG_LEVEL Environment Variable

**Переменная окружения:** `LOG_LEVEL`

**Возможные значения:**
- `DEBUG` — все логи, включая отладочные
- `INFO` — информационные логи и выше (по умолчанию)
- `WARNING` — предупреждения и ошибки
- `ERROR` — только ошибки и критические сообщения
- `CRITICAL` — только критические сообщения

**Применение:**
- Используется в root logger: `'level': os.getenv('LOG_LEVEL', 'INFO')`
- Используется во всех специфичных логгерах
- Применяется ко всем компонентам системы (Django, Celery, custom loggers)

### 3. Celery Logging Integration

**Расположение:** `coffee_payment/coffee_payment/celery.py`

**Интеграция:**
Celery автоматически использует Django logging configuration через:
```python
app.config_from_object('django.conf:settings', namespace='CELERY')
```

**Поведение:**
- Celery логи автоматически используют JSON formatter
- Уровень логирования контролируется через LOG_LEVEL
- Вывод в stdout/stderr

### 4. Custom Loggers

**Расположение:** Различные модули приложения (views.py, services/, tasks.py)

**Использование:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Поведение:**
- Автоматически наследуют конфигурацию от root logger
- Используют JSON formatter
- Выводят логи в stdout/stderr
- Уровень логирования контролируется через LOG_LEVEL

### 5. Docker Configuration

**Изменения в Dockerfile:**
- Удалена строка `RUN mkdir -p /app/logs`
- Удалены все ссылки на директорию logs

**Изменения в entrypoint.sh:**
- Удалены команды создания директории logs (если есть)

**Изменения в docker-compose.yml:**
- Удалены volume mappings для logs (если есть)

## Data Models

Изменения в моделях данных не требуются. Рефакторинг затрагивает только конфигурацию логирования.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Acceptence Criteria Testing Prework:

1.1 WHEN the System starts THEN the System SHALL output all logs to stdout for informational messages
Thoughts: This is about verifying that when the system is running, informational log messages (INFO, DEBUG, WARNING) are written to stdout. We can test this by capturing stdout during system operation and verifying that log messages appear there.
Testable: yes - property

1.2 WHEN the System starts THEN the System SHALL output all error logs to stderr for error messages
Thoughts: This is about verifying that error-level logs (ERROR, CRITICAL) are written to stderr. We can test this by capturing stderr during error conditions and verifying that error messages appear there.
Testable: yes - property

1.3 WHEN the System is configured THEN the System SHALL NOT create any file handlers for logging
Thoughts: This is about the configuration structure. We can inspect the LOGGING configuration dictionary and verify that no file handlers are present.
Testable: yes - example

1.4 WHEN the System is configured THEN the System SHALL NOT write logs to any files on disk
Thoughts: This is about runtime behavior. We can run the system and verify that no log files are created on disk.
Testable: yes - property

2.1 WHEN the Root Logger is configured THEN the System SHALL use JSON formatter for all log messages
Thoughts: This is about configuration. We can inspect the root logger configuration and verify it uses JSON formatter.
Testable: yes - example

2.2 WHEN a child logger inherits from Root Logger THEN the child logger SHALL use JSON formatter
Thoughts: This is about all child loggers. We can test this by creating random logger names, getting their formatters, and verifying they use JSON format.
Testable: yes - property

2.3 WHEN the System outputs a log message THEN the message SHALL be formatted as valid JSON
Thoughts: This applies to all log messages. We can capture log output and parse it as JSON to verify validity.
Testable: yes - property

2.4-2.7 WHEN the System outputs a log message THEN the JSON SHALL contain [field]
Thoughts: These are all checking that specific fields exist in the JSON output. We can combine these into one property that checks all required fields.
Testable: yes - property (combined)

3.1 WHEN the System reads configuration THEN the System SHALL read LOG_LEVEL environment variable
Thoughts: This is about configuration reading. We can set LOG_LEVEL and verify it's read correctly.
Testable: yes - example

3.2-3.6 WHEN LOG_LEVEL is set to [LEVEL] THEN the System SHALL log all messages at [LEVEL] and above
Thoughts: These are all testing the same behavior with different log levels. We can test this as a property across all valid log levels.
Testable: yes - property

3.7 WHEN LOG_LEVEL is not set THEN the System SHALL use INFO as default log level
Thoughts: This is testing a specific case - the default behavior.
Testable: yes - example

3.8-3.11 WHEN LOG_LEVEL is applied THEN [logger type] SHALL use the specified log level
Thoughts: These are all testing that different logger types respect LOG_LEVEL. We can test this as a property across different logger types.
Testable: yes - property

4.1 WHEN existing code calls logger methods THEN the System SHALL process the calls without errors
Thoughts: This is about backward compatibility. We can test that existing logger calls still work.
Testable: yes - property

5.1 WHEN the Docker container starts THEN the System SHALL NOT create any log directories
Thoughts: This is about Docker runtime behavior. We can inspect the container filesystem after startup.
Testable: yes - example

5.2 WHEN the Dockerfile is built THEN the Dockerfile SHALL NOT contain commands to create log directories
Thoughts: This is about the Dockerfile content. We can parse the Dockerfile and check for mkdir commands.
Testable: yes - example

6.1-6.6 Documentation requirements
Thoughts: These are about documentation content, not system behavior. Not automatically testable.
Testable: no

### Property Reflection

After reviewing all properties, I identify the following consolidations:

**Redundancy Analysis:**
- Properties 2.4-2.7 can be combined into a single property checking all required JSON fields
- Properties 3.2-3.6 can be combined into a single property testing log level filtering
- Properties 3.8-3.11 can be combined into a single property testing LOG_LEVEL application across logger types

**Unique Properties:**
1. Stdout output for informational logs (1.1)
2. Stderr output for error logs (1.2)
3. No file handlers in configuration (1.3)
4. No log files created on disk (1.4)
5. Root logger uses JSON formatter (2.1)
6. Child loggers inherit JSON formatter (2.2)
7. Log messages are valid JSON (2.3)
8. JSON contains all required fields (2.4-2.7 combined)
9. LOG_LEVEL environment variable is read (3.1)
10. Log level filtering works correctly (3.2-3.6 combined)
11. Default log level is INFO (3.7)
12. LOG_LEVEL applies to all logger types (3.8-3.11 combined)
13. Backward compatibility with existing code (4.1)
14. No log directories in container (5.1)
15. No mkdir commands in Dockerfile (5.2)

### Correctness Properties

Property 1: Informational logs output to stdout
*For any* log message at INFO, DEBUG, or WARNING level, when the system logs the message, the message should appear in stdout
**Validates: Requirements 1.1, 1.5, 1.6, 1.7**

Property 2: Error logs output to stderr
*For any* log message at ERROR or CRITICAL level, when the system logs the message, the message should appear in stderr
**Validates: Requirements 1.2**

Property 3: No log files created
*For any* system execution, after running the system, no log files should exist on disk in the logs directory
**Validates: Requirements 1.4**

Property 4: Child loggers inherit JSON formatting
*For any* logger name, when getting a logger instance, the logger should use JSON formatter inherited from root logger
**Validates: Requirements 2.2**

Property 5: Log messages are valid JSON
*For any* log message output, the message should be parseable as valid JSON
**Validates: Requirements 2.3**

Property 6: JSON contains required fields
*For any* log message output, the JSON should contain timestamp, tag (logger name), level, and message fields
**Validates: Requirements 2.4, 2.5, 2.6, 2.7**

Property 7: Log level filtering
*For any* LOG_LEVEL setting (DEBUG, INFO, WARNING, ERROR, CRITICAL), when LOG_LEVEL is set, only messages at that level and above should be output
**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6**

Property 8: LOG_LEVEL applies to all loggers
*For any* logger type (Django, Celery, custom), when LOG_LEVEL is set, the logger should respect the specified log level
**Validates: Requirements 3.8, 3.9, 3.10, 3.11**

Property 9: Backward compatibility
*For any* existing logger call in the codebase, the call should execute without errors after the refactoring
**Validates: Requirements 4.1, 4.2, 4.3**

## Error Handling

### Configuration Errors

**Scenario:** Invalid LOG_LEVEL value
**Handling:** 
- Django logging will use the default value (INFO)
- Log a warning message about invalid LOG_LEVEL value
- Continue with default configuration

**Scenario:** Missing LOG_LEVEL environment variable
**Handling:**
- Use default value INFO
- No error or warning needed (expected behavior)

### Runtime Errors

**Scenario:** StreamHandler fails to write to stdout/stderr
**Handling:**
- Python logging will handle this internally
- Fallback to sys.stderr for critical errors
- Application continues running

**Scenario:** JSON formatting fails
**Handling:**
- Python logging will fall back to default formatting
- Log the formatting error
- Continue with plain text output

### Docker Errors

**Scenario:** Container cannot write to stdout/stderr
**Handling:**
- This is a critical container configuration issue
- Container should fail to start
- Kubernetes will restart the container

## Testing Strategy

### Unit Tests

Unit tests will verify specific configuration and behavior:

1. **Configuration Tests:**
   - Verify LOGGING dictionary structure
   - Verify no file handlers present
   - Verify console handler configuration
   - Verify JSON formatter configuration
   - Verify root logger configuration

2. **LOG_LEVEL Tests:**
   - Test default value (INFO) when LOG_LEVEL not set
   - Test each valid LOG_LEVEL value (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Test invalid LOG_LEVEL value falls back to default

3. **Formatter Tests:**
   - Test JSON output structure
   - Test required fields presence
   - Test JSON validity

4. **Docker Tests:**
   - Verify Dockerfile doesn't contain mkdir for logs
   - Verify no log directories created in container

### Property-Based Tests

Property-based tests will verify universal properties across all inputs using Hypothesis library:

**Test Configuration:**
- Minimum 100 iterations per property test
- Use Hypothesis for generating test data
- Each test tagged with corresponding property from design document

**Property Tests:**

1. **Property 1: Informational logs to stdout**
   - Generate random log messages at INFO, DEBUG, WARNING levels
   - Verify all appear in stdout
   - **Feature: logging-refactoring, Property 1: Informational logs output to stdout**

2. **Property 2: Error logs to stderr**
   - Generate random log messages at ERROR, CRITICAL levels
   - Verify all appear in stderr
   - **Feature: logging-refactoring, Property 2: Error logs output to stderr**

3. **Property 3: No log files created**
   - Run system with random operations
   - Verify no files created in logs directory
   - **Feature: logging-refactoring, Property 3: No log files created**

4. **Property 4: Child loggers inherit JSON formatting**
   - Generate random logger names
   - Verify all use JSON formatter
   - **Feature: logging-refactoring, Property 4: Child loggers inherit JSON formatting**

5. **Property 5: Log messages are valid JSON**
   - Generate random log messages
   - Verify all output is valid JSON
   - **Feature: logging-refactoring, Property 5: Log messages are valid JSON**

6. **Property 6: JSON contains required fields**
   - Generate random log messages
   - Verify all contain timestamp, tag, level, message
   - **Feature: logging-refactoring, Property 6: JSON contains required fields**

7. **Property 7: Log level filtering**
   - Generate random LOG_LEVEL values
   - Generate random log messages at various levels
   - Verify only appropriate levels are output
   - **Feature: logging-refactoring, Property 7: Log level filtering**

8. **Property 8: LOG_LEVEL applies to all loggers**
   - Generate random logger types (Django, Celery, custom)
   - Set random LOG_LEVEL
   - Verify all loggers respect the level
   - **Feature: logging-refactoring, Property 8: LOG_LEVEL applies to all loggers**

9. **Property 9: Backward compatibility**
   - Test existing logger calls from codebase
   - Verify all execute without errors
   - **Feature: logging-refactoring, Property 9: Backward compatibility**

### Integration Tests

Integration tests will verify the system works correctly in realistic scenarios:

1. **End-to-End Logging Test:**
   - Start Django application
   - Trigger various operations (API calls, Celery tasks)
   - Capture stdout/stderr
   - Verify all logs appear in correct streams
   - Verify JSON format
   - Verify LOG_LEVEL is respected

2. **Docker Integration Test:**
   - Build Docker image
   - Run container
   - Verify no log directories created
   - Verify logs appear in container stdout/stderr
   - Verify Kubernetes can collect logs

3. **Celery Integration Test:**
   - Start Celery worker
   - Execute tasks
   - Verify Celery logs appear in stdout/stderr
   - Verify JSON format
   - Verify LOG_LEVEL is respected

### Manual Testing

Manual testing checklist:

1. **Local Development:**
   - Run application with different LOG_LEVEL values
   - Verify log output in terminal
   - Verify JSON format
   - Verify no log files created

2. **Docker Testing:**
   - Build and run Docker container
   - Check container logs: `docker logs <container>`
   - Verify JSON format
   - Verify no log directories in container

3. **Kubernetes Testing:**
   - Deploy to Kubernetes
   - Check pod logs: `kubectl logs <pod>`
   - Verify log aggregation system receives logs
   - Verify JSON parsing in log aggregation system

## Implementation Notes

### Migration Strategy

1. **Phase 1: Update Configuration**
   - Update LOGGING dictionary in settings.py
   - Add LOG_LEVEL environment variable support
   - Keep file handler temporarily for backward compatibility

2. **Phase 2: Update Docker**
   - Remove log directory creation from Dockerfile
   - Update docker-compose.yml
   - Update entrypoint.sh

3. **Phase 3: Remove File Handler**
   - Remove file handler from LOGGING configuration
   - Remove all references to log files
   - Update documentation

4. **Phase 4: Testing**
   - Run all tests
   - Verify logs in stdout/stderr
   - Deploy to staging environment
   - Verify log aggregation works

### Backward Compatibility

**Existing Code:**
- No changes required to existing logger calls
- All `logging.getLogger()` calls continue to work
- Custom loggers automatically inherit new configuration

**Configuration:**
- LOG_LEVEL is optional (defaults to INFO)
- System works without any environment variable changes

**Docker:**
- Existing deployments continue to work
- No breaking changes to container interface

### Performance Considerations

**Stdout/Stderr vs File:**
- Writing to stdout/stderr is generally faster than file I/O
- No disk I/O overhead
- No file rotation overhead
- Better for containerized environments

**JSON Formatting:**
- Minimal overhead (already used in current system)
- Efficient for log aggregation systems
- Better than plain text for parsing

**LOG_LEVEL:**
- Filtering at logger level (efficient)
- No performance impact compared to current system

### Security Considerations

**Sensitive Data:**
- Ensure no sensitive data (passwords, tokens) in log messages
- Review existing log messages for sensitive data
- Use existing logging practices

**Log Injection:**
- JSON format helps prevent log injection attacks
- Structured logging is safer than plain text

**Access Control:**
- Kubernetes RBAC controls access to pod logs
- Log aggregation system handles access control
- No file permissions to manage

## Documentation Updates

### README.md

Add section for LOG_LEVEL environment variable:

```markdown
### LOG_LEVEL

Controls the logging level for the entire application.

**Possible values:**
- `DEBUG` - All logs including debug messages
- `INFO` - Informational logs and above (default)
- `WARNING` - Warnings and errors only
- `ERROR` - Errors and critical messages only
- `CRITICAL` - Critical messages only

**Default:** `INFO`

**Example:**
```bash
export LOG_LEVEL=DEBUG
```
```

### PROJECT.md

Update logging section:

```markdown
## Logging System

The system uses structured JSON logging with output to stdout/stderr for compatibility with Kubernetes log aggregation.

**Key Features:**
- All logs output to stdout (INFO, DEBUG, WARNING) and stderr (ERROR, CRITICAL)
- JSON format for all log messages
- Centralized log level control via LOG_LEVEL environment variable
- Compatible with Loki, ELK, CloudWatch, and other log aggregation systems

**Configuration:**
- Set LOG_LEVEL environment variable to control verbosity
- Default level: INFO
- All loggers (Django, Celery, custom) respect LOG_LEVEL

**Log Format:**
```json
{
  "timestamp": "2025-11-24T10:30:00+00:00",
  "tag": "django.request",
  "level": "INFO",
  "message": "GET /v1/pay HTTP/1.1 200"
}
```

**No File Logging:**
- Logs are not written to files
- No log rotation needed
- Kubernetes handles log collection and retention
```

### PRODUCTION_DEPLOYMENT.md

Update deployment section:

```markdown
## Logging Configuration

The application outputs all logs to stdout/stderr in JSON format.

**Environment Variable:**
- `LOG_LEVEL` - Controls logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Default: INFO

**Kubernetes Configuration:**
- Logs are automatically collected by Kubernetes
- Configure log aggregation system (Loki, ELK, CloudWatch) to parse JSON logs
- Set appropriate retention policies in log aggregation system

**Monitoring:**
- Use log aggregation system to search and analyze logs
- Set up alerts based on ERROR and CRITICAL log levels
- Monitor log volume and performance
```
