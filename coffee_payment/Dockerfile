# Используем официальный образ Python в качестве базового
FROM python:3.12.8-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . /app

# Устанавливаем зависимости Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Копируем и делаем entrypoint.sh исполняемым
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Открываем порт для приложения (настраивается через GUNICORN_PORT)
# По умолчанию 8000, но в docker-compose используется 8080
EXPOSE 8000 8080

# Устанавливаем точку входа
ENTRYPOINT ["/app/entrypoint.sh"]

# По умолчанию запускаем в production режиме (Gunicorn)
# Для development режима установите ENV RUN_MODE=development