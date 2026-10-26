# import os
# import logging
# from flask import Flask, jsonify, request, render_template, abort, send_from_directory
# from flask_cors import CORS
# from cerberus import Validator
# import ipaddress
# import requests

# app = Flask(__name__, template_folder='templates')
# CORS(app) 

# # Настройка логирования
# if __name__ != '__main__':
#     gunicorn_logger = logging.getLogger('gunicorn.error')
#     app.logger.handlers = gunicorn_logger.handlers
#     app.logger.setLevel(gunicorn_logger.level)
#     logging.getLogger().handlers = gunicorn_logger.handlers
#     logging.getLogger().setLevel(gunicorn_logger.level)
# else:
#     logging.basicConfig(
#         level=logging.INFO,
#         format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
#     )
#     app.logger.setLevel(logging.INFO)

# PORT = int(os.environ.get("GALLERY_PORT", "8000"))
# IMAGES_DIR = os.environ.get("GALLERY_IMAGES_DIR", "/app/media")

# PROJECT_MAP = {
#     "terem-muhi-book": "Терем мухи",
#     "arthur_conan_doel_lost_world": "Затерянный мир",
#     "b_shergin_magic_ring": "Волшебное кольцо",
#     "illustrations_to_tail_about_fisher_and_fish": "Сказка о рыбаке и рыбке",
#     "l_n_tolstoy_assirian_king_assarkhadon": "Ассирийский царь Асархадон",
#     "tail_who_is_bigger": "Хвост, кто больше?",
#     "painters_book_diary_monstera": "Дневник монстеры"
# }

# schema = {"image_id": {"type": "string", "required": True}}
# v = Validator(schema)

# # 🌟 НОВЫЙ ЭНДПОИНТ: Сканирует папку проекта и возвращает список всех фото и видео
# @app.route('/api/project/<project_id>', methods=['GET'])
# def get_project_media(project_id):
#     project_dir = os.path.join(IMAGES_DIR, project_id)
    
#     if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
#         app.logger.warning(f"Директория проекта не найдена: {project_dir}")
#         return jsonify({"error": f"Project '{project_id}' not found"}), 404

#     allowed_extensions = {
#         '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.webp': 'image',
#         '.mp4': 'video', '.webm': 'video', '.ogg': 'video'
#     }

#     media_list = []
#     # Сортируем файлы по имени (01.jpg, 02.jpg, ...)
#     for filename in sorted(os.listdir(project_dir)):
#         ext = os.path.splitext(filename)[1].lower()
#         if ext in allowed_extensions:
#             media_type = allowed_extensions[ext]
#             media_list.append({
#                 "type": media_type,
#                 "src": f"/media/{project_id}/{filename}"
#             })

#     app.logger.info(f"Успешно получено {len(media_list)} медиафайлов для проекта {project_id}")
#     return jsonify({
#         "status": "success",
#         "project_id": project_id,
#         "title": PROJECT_MAP.get(project_id, project_id),
#         "media": media_list
#     })

# # 🌟 Исправлен возврат внешнего публичного URL (/media/...)
# @app.route('/api/image', methods=['GET'])
# def get_image_info():
#     image_id = request.args.get('image_id')
    
#     if not image_id or not v.validate({"image_id": image_id}):
#         return jsonify({"error": "Invalid or missing image_id"}), 400

#     file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")
    
#     if not os.path.exists(file_path):
#         return jsonify({"error": "Image not found"}), 404

#     return jsonify({
#         "status": "success",
#         "image_id": image_id,
#         "size": os.path.getsize(file_path),
#         "url": f"/media/{image_id}.jpg"
#     })

# @app.route('/media/<path:filename>')
# def serve_media(filename):
#     return send_from_directory(IMAGES_DIR, filename)

# def is_private_ip(ip_str):
#     try:
#         ip = ipaddress.ip_address(ip_str)
#         return ip.is_private or ip.is_loopback
#     except ValueError:
#         return True

# @app.route('/api/location', methods=['GET'])
# def get_user_location():
#     client_ip_from_js = request.args.get('client_ip')
#     raw_x_forwarded = request.headers.get('X-Forwarded-For')
#     remote_addr = request.remote_addr

#     if client_ip_from_js and not is_private_ip(client_ip_from_js):
#         target_ip = client_ip_from_js
#     elif raw_x_forwarded:
#         target_ip = raw_x_forwarded.split(',')[0].strip()
#     else:
#         target_ip = remote_addr

#     url = 'http://ip-api.com/json/?lang=ru' if is_private_ip(target_ip) else f'http://ip-api.com/json/{target_ip}?lang=ru'

#     try:
#         response = requests.get(url, timeout=3)
#         data = response.json()
#         if data.get('status') == 'success':
#             return jsonify({"status": "success", "ip": data.get('query', target_ip), "city": data.get('city', 'Неизвестный город')})
#         return jsonify({"status": "error", "message": "City not found"}), 404
#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=PORT)

import os
import logging
import time
import ipaddress
import requests
from flask import Flask, jsonify, request, render_template, abort, send_from_directory
from flask_cors import CORS
from cerberus import Validator

app = Flask(__name__, template_folder='templates')
CORS(app) 

# 🌟 1. НАСТРОЙКА ЛОГИРОВАНИЯ
if __name__ != '__main__':
    # Если запуск внутри Docker через Gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logging.getLogger().handlers = gunicorn_logger.handlers
    logging.getLogger().setLevel(gunicorn_logger.level)
else:
    # Локальный запуск через `python gallery.py`
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    app.logger.setLevel(logging.INFO)

PORT = int(os.environ.get("GALLERY_PORT", "8000"))
IMAGES_DIR = os.environ.get("GALLERY_IMAGES_DIR", "/app/media/nesessary/images")

PROJECT_MAP = {
    "terem-muhi-book": "Терем мухи",
    "arthur_conan_doel_lost_world": "Затерянный мир",
    "b_shergin_magic_ring": "Волшебное кольцо",
    "illustrations_to_tail_about_fisher_and_fish": "Сказка о рыбаке и рыбке",
    "l_n_tolstoy_assirian_king_assarkhadon": "Ассирийский царь Асархадон",
    "tail_who_is_bigger": "Хвост, кто больше?",
    "painters_book_diary_monstera": "Дневник монстеры"
}

schema = {"image_id": {"type": "string", "required": True}}
v = Validator(schema)


# 🌟 2. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ПОЛУЧЕНИЯ НАДЕЖНОГО IP-АДРЕСА
def get_client_ip():
    """Извлекает реальный IP-адрес пользователя с учетом Nginx прокси."""
    raw_x_forwarded = request.headers.get('X-Forwarded-For')
    if raw_x_forwarded:
        # Nginx может передать цепочку IP: "IP_клиента, IP_прокси"
        return raw_x_forwarded.split(',')[0].strip()
    return request.remote_addr or "Unknown IP"


# 🌟 3. MIDDLEWARE ДЛЯ ЧЁТКОГО ЛОГИРОВАНИЯ КАЖДОГО ЗАПРОСА
@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def log_request_info(response):
    # Игнорируем логирование запросов на favicon (чтобы не засорять вывод)
    if request.path == '/favicon.ico':
        return response

    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown Browser')
    duration_ms = round((time.time() - getattr(request, '_start_time', time.time())) * 1000, 2)
    
    # Структурированная строка лога для любого запроса
    app.logger.info(
        f"[REQ] Client IP: {client_ip} | Method: {request.method} | Path: {request.path} | "
        f"Status: {response.status_code} | Duration: {duration_ms}ms | User-Agent: {user_agent}"
    )
    return response


# 🌟 4. ЭНДПОИНТЫ API
@app.route('/api/project/<project_id>', methods=['GET'])
def get_project_media(project_id):
    client_ip = get_client_ip()
    project_dir = os.path.join(IMAGES_DIR, project_id)
    
    if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
        app.logger.warning(f"[PROJECT 404] IP: {client_ip} запросил несуществующий проект '{project_id}'")
        return jsonify({"error": f"Project '{project_id}' not found"}), 404

    allowed_extensions = {
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.webp': 'image',
        '.mp4': 'video', '.webm': 'video', '.ogg': 'video'
    }

    media_list = []
    for filename in sorted(os.listdir(project_dir)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in allowed_extensions:
            media_type = allowed_extensions[ext]
            media_list.append({
                "type": media_type,
                "src": f"/media/{project_id}/{filename}"
            })

    app.logger.info(f"[PROJECT SUCCESS] IP: {client_ip} просматривает проект '{project_id}' ({len(media_list)} файлов)")
    return jsonify({
        "status": "success",
        "project_id": project_id,
        "title": PROJECT_MAP.get(project_id, project_id),
        "media": media_list
    })

@app.route('/api/image', methods=['GET'])
def get_image_info():
    image_id = request.args.get('image_id')
    client_ip = get_client_ip()
    
    if not image_id or not v.validate({"image_id": image_id}):
        return jsonify({"error": "Invalid or missing image_id"}), 400

    file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")
    
    if not os.path.exists(file_path):
        app.logger.warning(f"[IMAGE 404] IP: {client_ip} запросил файл '{image_id}.jpg'")
        return jsonify({"error": "Image not found"}), 404

    return jsonify({
        "status": "success",
        "image_id": image_id,
        "size": os.path.getsize(file_path),
        "url": f"/media/{image_id}.jpg"
    })

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(IMAGES_DIR, filename)

def is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return True

@app.route('/api/location', methods=['GET'])
def get_user_location():
    client_ip_from_js = request.args.get('client_ip')
    raw_x_forwarded = request.headers.get('X-Forwarded-For')
    remote_addr = request.remote_addr

    if client_ip_from_js and not is_private_ip(client_ip_from_js):
        target_ip = client_ip_from_js
    elif raw_x_forwarded:
        target_ip = raw_x_forwarded.split(',')[0].strip()
    else:
        target_ip = remote_addr

    url = 'http://ip-api.com/json/?lang=ru' if is_private_ip(target_ip) else f'http://ip-api.com/json/{target_ip}?lang=ru'

    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get('status') == 'success':
            city = data.get('city', 'Неизвестный город')
            resolved_ip = data.get('query', target_ip)
            app.logger.info(f"[GEOIP SUCCESS] Определен город '{city}' для IP '{resolved_ip}'")
            return jsonify({"status": "success", "ip": resolved_ip, "city": city})
        return jsonify({"status": "error", "message": "City not found"}), 404
    except Exception as e:
        app.logger.error(f"[GEOIP ERROR] Ошибка выполнения: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)