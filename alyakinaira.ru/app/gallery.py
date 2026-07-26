import os
import logging
from flask import Flask, jsonify, request, render_template, abort, send_from_directory
from flask_cors import CORS
from cerberus import Validator
import ipaddress
import requests

app = Flask(__name__, template_folder='templates')
CORS(app) 

# 🌟 НАДЕЖНАЯ НАСТРОЙКА ЛОГИРОВАНИЯ ДЛЯ FLASK + GUNICORN
if __name__ != '__main__':
    # Если запуск под Gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    
    # 1. Назначаем обработчики Gunicorn для логгера Flask
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    
    # 2. Перенаправляем корневой логгер Python в Gunicorn, чтобы логи за пределами app.logger тоже работали
    logging.getLogger().handlers = gunicorn_logger.handlers
    logging.getLogger().setLevel(gunicorn_logger.level)
else:
    # Для локальной разработки через python gallery.py
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    app.logger.setLevel(logging.INFO)

PORT = int(os.environ.get("GALLERY_PORT", "8000"))
IMAGES_DIR = os.environ.get("GALLERY_IMAGES_DIR", "/app/media")

# Ключи карты
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

# Динамический роутер страниц проектов
@app.route('/project/<project_id>')
def render_project_page(project_id):
    if project_id not in PROJECT_MAP:
        app.logger.warning(f"Project not found: {project_id}")
        abort(404)
    
    title = PROJECT_MAP[project_id]
    return render_template('project_template.html', project_name=project_id, project_title=title)

# API эндпоинт получения информации об изображении
@app.route('/api/image', methods=['GET'])
def get_image_info():
    image_id = request.args.get('image_id')
    
    if not image_id:
        app.logger.warning("API call failed: Missing image_id")
        return jsonify({"error": "Missing image_id"}), 400
        
    if not v.validate({"image_id": image_id}):
        app.logger.warning(f"API call failed: Invalid image_id '{image_id}'")
        return jsonify({"error": "Invalid image_id"}), 400

    file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")

    if not os.path.exists(file_path):
        app.logger.error(f"Image file not found: {file_path}")
        return jsonify({"error": "Image not found"}), 404

    app.logger.info(f"Image info retrieved successfully for: {image_id}")
    return jsonify({
        "status": "success",
        "image_id": image_id,
        "size": os.path.getsize(file_path),
        "url": f"/nesessary/images/{image_id}.jpg"
    })

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(IMAGES_DIR, filename)

def is_private_ip(ip_str):
    """Проверяет, является ли IP-адрес приватным/локальным (127.0.0.1, 192.168.x.x, 100.x.x.x Tailscale и т.д.)"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return True

# 🌟 Обновленный маршрут /api/location с детализированными логами
@app.route('/api/location', methods=['GET'])
def get_user_location():
    app.logger.info("=== [GeoIP] Начало обработки запроса /api/location ===")
    
    # 1. Считываем IP, полученный напрямую от клиентского браузера
    client_ip_from_js = request.args.get('client_ip')
    
    raw_x_forwarded = request.headers.get('X-Forwarded-For')
    remote_addr = request.remote_addr

    app.logger.info(f"[GeoIP] [Шаг 1] JS client_ip='{client_ip_from_js}', X-Forwarded-For='{raw_x_forwarded}', remote_addr='{remote_addr}'")

    # Приоритет 1: IP, определенный на стороне клиента (JS)
    if client_ip_from_js and not is_private_ip(client_ip_from_js):
        target_ip = client_ip_from_js
        app.logger.info(f"[GeoIP] [Шаг 2] Используем клиентский публичный IP от JS: '{target_ip}'")
    # Приоритет 2: X-Forwarded-For от Nginx
    elif raw_x_forwarded:
        target_ip = raw_x_forwarded.split(',')[0].strip()
        app.logger.info(f"[GeoIP] [Шаг 2] Используем IP из X-Forwarded-For: '{target_ip}'")
    # Приоритет 3: remote_addr
    else:
        target_ip = remote_addr
        app.logger.info(f"[GeoIP] [Шаг 2] Используем remote_addr: '{target_ip}'")

    # Проверяем итоговый IP
    if is_private_ip(target_ip):
        url = 'http://ip-api.com/json/?lang=ru'
        app.logger.info(f"[GeoIP] [Шаг 3] IP '{target_ip}' является приватным/локальным. Запрашиваем внешнюю геопозицию сервера: {url}")
    else:
        url = f'http://ip-api.com/json/{target_ip}?lang=ru'
        app.logger.info(f"[GeoIP] [Шаг 3] Запрос геолокации для публичного IP: {url}")

    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        app.logger.info(f"[GeoIP] [Шаг 4] Ответ ip-api: {data}")

        if data.get('status') == 'success':
            city = data.get('city', 'Неизвестный город')
            resolved_ip = data.get('query', target_ip)
            app.logger.info(f"[GeoIP] [Успех] Определен город '{city}' для IP '{resolved_ip}'")
            return jsonify({
                "status": "success",
                "ip": resolved_ip,
                "city": city
            })
        else:
            reason = data.get('message', 'Unknown failure')
            app.logger.warning(f"[GeoIP] [Ошибка API] ip-api вернул статус 'fail': '{reason}'")
            return jsonify({"status": "error", "message": "City not found"}), 404

    except Exception as e:
        app.logger.error(f"[GeoIP] [Исключение] Ошибка выполнения: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to resolve IP"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
