FROM python:3.12-alpine
WORKDIR /app

# 1. Оптимизация Python для Docker/Kubernetes:
# PYTHONDONTWRITEBYTECODE=1 — запрещает создавать .pyc файлы (контейнер весит меньше)
# PYTHONUNBUFFERED=1 — отключает буферизацию (логи мгновенно улетают в stdout/stderr)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 2. Установка зависимостей (вынесено выше копирования кода для кэширования слоев Docker)
RUN pip install --no-cache-dir flask gunicorn flask-cors cerberus pillow requests

# 3. Копируем файлы приложения
COPY gallery.py .
COPY templates/ ./templates

EXPOSE 8000

# 4. Запуск приложения:
# Мы заменили пути к файлам на "-" — в Gunicorn это означает "выводить напрямую в stdout/stderr".
# Также убрали --capture-output, так как при PYTHONUNBUFFERED=1 логи Flask и так сразу летят в консоль.
CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "gallery:app"]
