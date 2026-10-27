FROM python:3.14-alpine
WORKDIR /app
COPY requirements-proxy.txt .
RUN pip install --no-cache-dir gunicorn flask flask-cors requests redis
COPY redis_proxy.py .
EXPOSE 8001
CMD ["gunicorn", "--workers", "4", "--threads", "2", "--timeout", "60", "--bind", "0.0.0.0:8001", "redis_proxy:app"]
