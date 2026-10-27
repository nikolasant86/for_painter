# import os
# import logging
# import time
# import traceback
# import requests
# import redis
# from flask import Flask, jsonify, request, Response
# from flask_cors import CORS

# app = Flask(__name__)
# CORS(app)

# ORIGINAL_BACKEND_URL = os.environ.get("ORIGINAL_BACKEND_URL", "http://gallery:8000")
# REDIS_HOST = os.environ.get("REDIS_HOST", "redis-cache-service")
# REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
# PROXY_PORT = int(os.environ.get("PROXY_PORT", "8001"))
# CACHE_TIMEOUT = 7200  # 2 часа

# logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in PROXY: %(message)s')

# def get_client_ip():
#     raw_x_forwarded = request.headers.get('X-Forwarded-For')
#     if raw_x_forwarded:
#         clean_str = raw_x_forwarded.replace(" ", "")
#         return clean_str.split(',')[0]
#     return str(request.remote_addr or "127.0.0.1")

# @app.before_request
# def start_timer():
#     request._start_time = time.time()

# @app.after_request
# def log_proxy_info(response):
#     if request.path == '/favicon.ico':
#         return response
#     duration_ms = round((time.time() - getattr(request, '_start_time', time.time())) * 1000, 2)
#     app.logger.info(f"[PROXY REQ] Path: {request.path} | Status: {response.status_code} | Duration: {duration_ms}ms")
#     return response

# @app.errorhandler(Exception)
# def handle_exception(e):
#     app.logger.error(f"!!! [PROXY CRITICAL ERROR]: {str(e)}")
#     app.logger.error(traceback.format_exc())
#     return jsonify({"error": "Internal Proxy Error", "message": str(e)}), 500

# @app.route('/', defaults={'path': ''}, methods=['GET'])
# @app.route('/<path:path>', methods=['GET'])
# def proxy_all(path):
#     if path.startswith('media/'):
#         return handle_media_cache(path)
#     if path == 'api/location':
#         return handle_location_cache()

#     cache_key = f"text_cache:{request.full_path}"
#     force_refresh = request.headers.get('Cache-Control') == 'no-cache'
    
#     if not force_refresh:
#         try:
#             cached_response = r.get(cache_key)
#             if cached_response:
#                 return cached_response, 200, {'Content-Type': 'application/json' if path.startswith('api/') else 'text/html; charset=utf-8'}
#         except Exception as cache_err:
#             app.logger.error(f"Redis error: {cache_err}")

#     try:
#         response = requests.get(f"{ORIGINAL_BACKEND_URL}/{path}", params=request.args, timeout=15)
#         if response.status_code == 200:
#             try:
#                 r.set(cache_key, response.content, ex=CACHE_TIMEOUT) # Используем современный синтаксис
#             except Exception as cache_err:
#                 app.logger.error(f"Failed to write to Redis: {cache_err}")
#         return response.content, response.status_code, dict(response.headers)
#     except Exception as e:
#         return jsonify({"error": "Original backend unavailable"}), 502

# def handle_location_cache():
#     client_ip = get_client_ip()
#     cache_key = f"proxy:location:{client_ip}"
#     try:
#         cached_data = r.get(cache_key)
#         if cached_data:
#             return cached_data, 200, {'Content-Type': 'application/json'}
#     except Exception:
#         pass
        
#     try:
#         response = requests.get(f"{ORIGINAL_BACKEND_URL}/api/location", params=request.args, timeout=5)
#         if response.status_code == 200:
#             r.set(cache_key, response.content, ex=86400) # Кэш на 24 часа
#         return response.content, response.status_code, dict(response.headers)
#     except Exception:
#         return jsonify({"error": "Original backend unavailable"}), 502

# def handle_media_cache(path):
#     cache_key = f"media_cache:{path}"
#     try:
#         cached_file = r.get(cache_key)
#         cached_meta = r.get(f"{cache_key}:type")
#         if cached_file and cached_meta:
#             return Response(cached_file, mimetype=cached_meta.decode('utf-8'))
#     except Exception:
#         pass

#     try:
#         response = requests.get(f"{ORIGINAL_BACKEND_URL}/{path}", timeout=30)
#         if response.status_code == 200:
#             content_type = response.headers.get('Content-Type', 'application/octet-stream')
#             try:
#                 r.set(cache_key, response.content, ex=CACHE_TIMEOUT)
#                 r.set(f"{cache_key}:type", content_type.encode('utf-8'), ex=CACHE_TIMEOUT)
#             except Exception:
#                 pass
#             return Response(response.content, mimetype=content_type)
#         return response.content, response.status_code, dict(response.headers)
#     except Exception:
#         return jsonify({"error": "Media server unavailable"}), 502

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=PROXY_PORT)

import os
import logging
import time
import traceback
import json
import requests
import redis
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ⚙️ НАСТРОЙКИ СЕТИ И БЕЗОПАСНОСТИ ДЛЯ PRODUCTION
ORIGINAL_BACKEND_URL = os.environ.get("ORIGINAL_BACKEND_URL", "http://gallery:8000")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-cache-service")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)  # Подтягивается из Kubernetes Secret

# Подключение к Redis (decode_responses=False для корректного кэширования бинарных файлов)
r = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    password=REDIS_PASSWORD, 
    decode_responses=False
)

CACHE_TIMEOUT = 7200  # Тотальный кэш на 2 часа (в секундах)

# Настройка системного логирования под стандарты Kubernetes (JSON)
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "component": "PROXY-CACHE",
            "message": record.getMessage()
        }
        return json.dumps(log_data)

logger = logging.getLogger("proxy_logger")
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Изолируем стандартные логи Flask, чтобы не дублировать записи
logging.getLogger('wsgi').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Безопасное извлечение реального IP пользователя
def get_client_ip():
    raw_x_forwarded = request.headers.get('X-Forwarded-For')
    if raw_x_forwarded:
        # Убираем пробелы и берем самый первый IP в цепочке (клиентский)
        ips = [ip.strip() for ip in raw_x_forwarded.split(',')]
        if ips:
            return ips[0]
    return str(request.remote_addr or "127.0.0.1")

@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def log_request_result(response):
    if request.path == '/favicon.ico':
        return response
        
    duration_ms = round((time.time() - getattr(request, '_start_time', time.time())) * 1000, 2)
    client_ip = get_client_ip()
    
    # Структурированный лог для продакшена
    log_payload = {
        "client_ip": client_ip,
        "method": request.method,
        "path": request.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "user_agent": request.headers.get('User-Agent', 'Unknown')
    }
    logger.info(f"Request processed: {json.dumps(log_payload)}")
    return response

# Перехватчик критических ошибок (убирает молчаливый статус 502)
@app.errorhandler(Exception)
def handle_internal_exception(e):
    error_details = {
        "error": str(e),
        "traceback": traceback.format_exc()
    }
    logger.error(f"CRITICAL ERROR EXCEPTION: {json.dumps(error_details)}")
    return jsonify({"error": "Internal Proxy Error", "message": str(e)}), 500


# 🌟 1. ОБЩИЙ ОБРАБОТЧИК (HTML, JSON API, ТЕКСТ)
@app.route('/', defaults={'path': ''}, methods=['GET'])
@app.route('/<path:path>', methods=['GET'])
def proxy_gateway(path):
    # Разделение логики на бинарный и текстовый кэш
    if path.startswith('media/'):
        return handle_binary_media_cache(path)
        
    if path == 'api/location':
        return handle_user_location_cache()

    cache_key = f"text_cache:{request.full_path}"
    force_refresh = request.headers.get('Cache-Control') == 'no-cache'
    
    if not force_refresh:
        try:
            cached_response = r.get(cache_key)
            if cached_response:
                content_type = 'application/json' if path.startswith('api/') else 'text/html; charset=utf-8'
                return cached_response, 200, {'Content-Type': content_type, 'X-Cache': 'HIT'}
        except Exception as cache_err:
            logger.error(f"Redis read error for key {cache_key}: {str(cache_err)}")

    try:
        response = requests.get(f"{ORIGINAL_BACKEND_URL}/{path}", params=request.args, timeout=15)
        if response.status_code == 200:
            try:
                r.set(cache_key, response.content, ex=CACHE_TIMEOUT)
            except Exception as cache_err:
                logger.error(f"Redis write error for key {cache_key}: {str(cache_err)}")
        return response.content, response.status_code, dict(response.headers)
    except Exception as e:
        logger.error(f"Backend connection failed ({ORIGINAL_BACKEND_URL}/{path}): {str(e)}")
        return jsonify({"error": "Original backend unavailable"}), 502


# 🌟 2. КЭШИРОВАНИЕ ГЕОЛОКАЦИИ ПО IP (2 ЧАСА)
def handle_user_location_cache():
    client_ip = get_client_ip()
    cache_key = f"proxy:location:{client_ip}"
    
    try:
        cached_data = r.get(cache_key)
        if cached_data:
            return cached_data, 200, {'Content-Type': 'application/json', 'X-Cache': 'HIT'}
    except Exception as cache_err:
        logger.error(f"Redis location read error: {str(cache_err)}")
        
    try:
        response = requests.get(f"{ORIGINAL_BACKEND_URL}/api/location", params=request.args, timeout=5)
        if response.status_code == 200:
            try:
                r.set(cache_key, response.content, ex=7200)  # Жесткий кэш геоданных на 2 часа
            except Exception as cache_err:
                logger.error(f"Redis location write error: {str(cache_err)}")
        return response.content, response.status_code, dict(response.headers)
    except Exception as e:
        logger.error(f"Location endpoint communication failed: {str(e)}")
        return jsonify({"error": "Original backend unavailable"}), 502


# 🌟 3. ТОТАЛЬНОЕ КЭШИРОВАНИЕ ИЗОБРАЖЕНИЙ И ВИДЕО (БИНАРНЫЕ ДАННЫЕ)
def handle_binary_media_cache(path):
    cache_key = f"media_cache:{path}"
    
    try:
        cached_file = r.get(cache_key)
        cached_meta = r.get(f"{cache_key}:type")
        
        if cached_file and cached_meta:
            return Response(cached_file, mimetype=cached_meta.decode('utf-8'), headers={'X-Cache': 'HIT'})
    except Exception as cache_err:
        logger.error(f"Redis media read error for {path}: {str(cache_err)}")

    try:
        response = requests.get(f"{ORIGINAL_BACKEND_URL}/{path}", timeout=30)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            try:
                # Запись бинарного контента и метаданных типа файла
                r.set(cache_key, response.content, ex=CACHE_TIMEOUT)
                r.set(f"{cache_key}:type", content_type.encode('utf-8'), ex=CACHE_TIMEOUT)
            except Exception as cache_err:
                logger.error(f"Redis media write error for {path}: {str(cache_err)}")
            
            return Response(response.content, mimetype=content_type)
        return response.content, response.status_code, dict(response.headers)
    except Exception as e:
        logger.error(f"Failed to fetch media source from backend ({path}): {str(e)}")
        return jsonify({"error": "Media server unavailable"}), 502

if __name__ == '__main__':
    # Используется только для локальной отладки вне докера
    app.run(host='0.0.0.0', port=8001)
