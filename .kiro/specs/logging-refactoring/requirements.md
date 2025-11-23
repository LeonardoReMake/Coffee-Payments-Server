# Requirements Document

## Introduction

Данный документ описывает требования к рефакторингу системы логирования в проекте Coffee Payments Server. Цель — привести систему логирования в соответствие с требованиями продового окружения и обеспечить совместимость с лог-агрегацией Kubernetes (Loki/ELK/CloudWatch).

## Glossary

- **System** — Coffee Payments Server (Django приложение с Celery)
- **Logger** — компонент системы логирования, отвечающий за запись логов
- **Handler** — обработчик логов, определяющий куда записываются логи (файл, консоль, сеть)
- **Formatter** — форматтер логов, определяющий формат записи логов (JSON, plain text)
- **Root Logger** — корневой логгер, от которого наследуются все остальные логгеры
- **stdout** — стандартный поток вывода (standard output)
- **stderr** — стандартный поток ошибок (standard error)
- **JSON Format** — формат логов в виде JSON объектов
- **LOG_LEVEL** — переменная окружения для управления уровнем логирования

## Requirements

### Requirement 1

**User Story:** Как DevOps инженер, я хочу, чтобы все логи выводились только в stdout/stderr, чтобы Kubernetes мог собирать их через стандартные механизмы лог-агрегации.

#### Acceptance Criteria

1. WHEN the System starts THEN the System SHALL output all logs to stdout for informational messages
2. WHEN the System starts THEN the System SHALL output all error logs to stderr for error messages
3. WHEN the System is configured THEN the System SHALL NOT create any file handlers for logging
4. WHEN the System is configured THEN the System SHALL NOT write logs to any files on disk
5. WHEN Django logs a message THEN the System SHALL output the message to stdout or stderr
6. WHEN Celery logs a message THEN the System SHALL output the message to stdout or stderr
7. WHEN custom loggers log a message THEN the System SHALL output the message to stdout or stderr

### Requirement 2

**User Story:** Как DevOps инженер, я хочу, чтобы все логи были в JSON формате, чтобы лог-агрегаторы могли легко парсить и индексировать их.

#### Acceptance Criteria

1. WHEN the Root Logger is configured THEN the System SHALL use JSON formatter for all log messages
2. WHEN a child logger inherits from Root Logger THEN the child logger SHALL use JSON formatter
3. WHEN the System outputs a log message THEN the message SHALL be formatted as valid JSON
4. WHEN the System outputs a log message THEN the JSON SHALL contain timestamp field
5. WHEN the System outputs a log message THEN the JSON SHALL contain log level field
6. WHEN the System outputs a log message THEN the JSON SHALL contain logger name field
7. WHEN the System outputs a log message THEN the JSON SHALL contain message field
8. WHEN the System is configured THEN the System SHALL NOT output any plain text formatted logs

### Requirement 3

**User Story:** Как DevOps инженер, я хочу управлять уровнем логирования через единую переменную окружения, чтобы легко настраивать детализацию логов в разных окружениях.

#### Acceptance Criteria

1. WHEN the System reads configuration THEN the System SHALL read LOG_LEVEL environment variable
2. WHEN LOG_LEVEL is set to DEBUG THEN the System SHALL log all messages at DEBUG level and above
3. WHEN LOG_LEVEL is set to INFO THEN the System SHALL log all messages at INFO level and above
4. WHEN LOG_LEVEL is set to WARNING THEN the System SHALL log all messages at WARNING level and above
5. WHEN LOG_LEVEL is set to ERROR THEN the System SHALL log all messages at ERROR level and above
6. WHEN LOG_LEVEL is set to CRITICAL THEN the System SHALL log all messages at CRITICAL level only
7. WHEN LOG_LEVEL is not set THEN the System SHALL use INFO as default log level
8. WHEN LOG_LEVEL is applied THEN the Root Logger SHALL use the specified log level
9. WHEN LOG_LEVEL is applied THEN all Django loggers SHALL use the specified log level
10. WHEN LOG_LEVEL is applied THEN all Celery loggers SHALL use the specified log level
11. WHEN LOG_LEVEL is applied THEN all custom loggers SHALL use the specified log level

### Requirement 4

**User Story:** Как разработчик, я хочу, чтобы система логирования была совместима с существующим кодом, чтобы не требовалось переписывать все вызовы логгеров.

#### Acceptance Criteria

1. WHEN existing code calls logger methods THEN the System SHALL process the calls without errors
2. WHEN existing code uses custom loggers THEN the custom loggers SHALL inherit JSON formatting from Root Logger
3. WHEN existing code logs messages THEN the messages SHALL be output in JSON format to stdout/stderr

### Requirement 5

**User Story:** Как DevOps инженер, я хочу, чтобы Docker контейнер не создавал директории для логов, чтобы упростить файловую систему контейнера.

#### Acceptance Criteria

1. WHEN the Docker container starts THEN the System SHALL NOT create any log directories
2. WHEN the Dockerfile is built THEN the Dockerfile SHALL NOT contain commands to create log directories
3. WHEN the entrypoint script runs THEN the script SHALL NOT create any log directories

### Requirement 6

**User Story:** Как разработчик, я хочу, чтобы документация была обновлена с описанием новой переменной LOG_LEVEL, чтобы другие разработчики понимали как управлять логированием.

#### Acceptance Criteria

1. WHEN the README.md is updated THEN the README.md SHALL contain description of LOG_LEVEL environment variable
2. WHEN the README.md is updated THEN the README.md SHALL contain possible values for LOG_LEVEL
3. WHEN the README.md is updated THEN the README.md SHALL contain default value for LOG_LEVEL
4. WHEN the PROJECT.md is updated THEN the PROJECT.md SHALL contain description of the new logging system
5. WHEN the PROJECT.md is updated THEN the PROJECT.md SHALL contain information about JSON format logging
6. WHEN the PROJECT.md is updated THEN the PROJECT.md SHALL contain information about stdout/stderr output
