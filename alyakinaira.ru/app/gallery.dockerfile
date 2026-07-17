FROM python:3.12-alpine
WORKDIR /app

# Копируем только файлы приложения (скрипт и папка templates)
COPY gallery.py .
COPY templates/ ./templates

# Устанавливаем необходимые зависимости
RUN pip install --no-cache-dir flask gunicorn flask-cors cerberus pillow requests

EXPOSE 8000

# Запуск приложения через WSGI сервер Gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "gallery:app"]
