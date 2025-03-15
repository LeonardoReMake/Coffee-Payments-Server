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

# Открываем порт для приложения
EXPOSE 8080

# Устанавливаем точку входа
ENTRYPOINT ["/app/entrypoint.sh"]

# Запускаем сервер Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8080"]