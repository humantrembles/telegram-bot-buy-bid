# Используем конкретную, легковесную и безопасную версию Python
FROM python:3.11-slim-bullseye

# Не буферизуем вывод, чтобы print() сразу шел в логи
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /bot

# Копируем файл с зависимостями в рабочую директорию
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Команда для запуска остается той же. Предполагая, что ваш файл называется aiogram_run.py
CMD ["/bin/bash", "-c", "python aiogram_run.py"]