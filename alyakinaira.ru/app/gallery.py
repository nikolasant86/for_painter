import os
import logging
from flask import Flask, jsonify, request, render_template, abort, send_from_directory
from flask_cors import CORS
from cerberus import Validator
import ipaddress
import requests
import glob
from datetime import datetime
import sys

app = Flask(__name__, template_folder='templates')
CORS(app) 

# === НАСТРОЙКА ЛОГИРОВАНИЯ ДЛЯ СРЕДЫ ОРКЕСТРАЦИИ (DOCKER / K8S) ===
if __name__ != '__main__':
    # Если запуск под Gunicorn (внутри Docker/K8s)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logging.getLogger().handlers = gunicorn_logger.handlers
    logging.getLogger().setLevel(gunicorn_logger.level)
else:
    # Локальный ручной запуск
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    app.logger.setLevel(logging.INFO)

# Инициализируем логгер аналитики, который пишет в stdout.
# В K8s это позволит собирать логи стандартными агентами логирования (Loki/Fluentd).
analytics_logger = logging.getLogger('analytics_stream')
analytics_logger.setLevel(logging.INFO)

# Проверяем, чтобы не дублировать обработчики при перезапусках Flask
if not analytics_logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    # Используем JSON-подобный или легко парсящийся формат для Grafana/Loki
    stream_formatter = logging.Formatter('%(message)s')
    stream_handler.setFormatter(stream_formatter)
    analytics_logger.addHandler(stream_handler)

PORT = int(os.environ.get("GALLERY_PORT", "8000"))
IMAGES_DIR = os.environ.get("GALLERY_IMAGES_DIR", "/app/media")

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


# === КОНТУР 2: АВТОМАТИЧЕСКИЙ ПЕРЕХВАТ БОТОВ И СКАНЕРОВ ===

def get_server_side_ip(target_ip):
    """Вспомогательный метод: если IP-пакет пришел маскированным от роутера (192.168.1.1),
    мы делаем запрос к внешнему GeoIP, чтобы зафиксировать хотя бы внешнюю точку выхода сети."""
    if target_ip == "192.168.1.1" or is_private_ip(target_ip):
        try:
            # Запрашиваем данные о внешнем подключении самого сервера
            res = requests.get('http://ip-api.com', timeout=2).json()
            if res.get('status') == 'success':
                return f"{res.get('query')} (ISP: {res.get('isp')}, City: {res.get('city')})"
        except Exception:
            pass
    return target_ip

@app.before_request
def intercept_bot_scanning():
    path = request.path
    # Список типичных триггеров сканирования вредоносных ботов
    bot_signatures = ['.env', 'wp-admin', 'wp-login', 'config', 'admin', '.git', 'xmlrpc']
    
    if any(sig in path.lower() for sig in bot_signatures):
        raw_ip = request.remote_addr
        resolved_ip = get_server_side_ip(raw_ip)
        
        log_msg = f"[⚠️ БОТ/СКАНЕР] Обнаружена попытка взлома! Путь: '{path}' | Сетевой IP роутера: {raw_ip} | Вычисленный внешний хост сервера: {resolved_ip} | Юзер-агент: {request.user_agent.string}"
        analytics_logger.warning(log_msg)
        app.logger.warning(log_msg)
        # Сразу обрываем соединение для бота
        abort(403)

@app.errorhandler(404)
def page_not_found(e):
    raw_ip = request.remote_addr
    path = request.path
    resolved_ip = get_server_side_ip(raw_ip)
    
    log_msg = f"[🚫 ОШИБКА 404] Запрос к несуществующему ресурсу: '{path}' | Локальный IP пакета: {raw_ip} | Примерный внешний хост: {resolved_ip} | Ссылка: {request.referrer}"
    analytics_logger.info(log_msg)
    
    # Возвращаем стандартный JSON или рендерим вашу 404 страницу
    return jsonify({"error": "Resource not found"}), 404


# === КОНТУР 1: ПРИЕМ РЕАЛЬНЫХ IP-АДРЕСОВ ОТ КЛИЕНТСКОГО JS ===

@app.route('/api/analytics-log', methods=['POST'])
def receive_client_analytics():
    data = request.get_json() or {}
    client_ip = data.get('ip', 'Unknown_IP')
    current_url = data.get('url', 'Unknown_URL')
    user_agent = data.get('user_agent', 'Unknown_UA')
    city = data.get('city', 'Unknown_City')
    
    # Записываем чистый лог в analytics.log
    log_msg = f"[👤 ЖИВОЙ ПОСЕТИТЕЛЬ] Реальный IP: {client_ip} [{city}] | Перешел на: {current_url} | Браузер: {user_agent}"
    analytics_logger.info(log_msg)
    app.logger.info(log_msg)
    
    return jsonify({"status": "logged"}), 200


# === ОСТАЛЬНЫЕ СТАНДАРТНЫЕ МАРШРУТЫ ПРИЛОЖЕНИЯ ===

@app.route('/project/<project_id>')
def render_project_page(project_id):
    if project_id not in PROJECT_MAP:
        app.logger.warning(f"Project not found: {project_id}")
        abort(404)
    title = PROJECT_MAP[project_id]
    return render_template('project_template.html', project_name=project_id, project_title=title)

@app.route('/api/project-images/<project_id>', methods=['GET'])
def get_project_images(project_id):
    if project_id not in PROJECT_MAP:
        return jsonify({"error": "Project not found"}), 404
    project_dir = os.path.join(IMAGES_DIR, "nesessary", "images", project_id)
    search_path = os.path.join(project_dir, "*.jpg")
    try:
        full_paths = sorted(glob.glob(search_path))
        image_urls = [f"/media/nesessary/images/{project_id}/{os.path.basename(p)}" for p in full_paths]
        return jsonify({"status": "success", "project_id": project_id, "images": image_urls})
    except Exception as e:
        app.logger.error(f"Error scanning directory: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/image', methods=['GET'])
def get_image_info():
    image_id = request.args.get('image_id')
    if not image_id or not v.validate({"image_id": image_id}):
        return jsonify({"error": "Invalid or missing image_id"}), 400
    file_path = f"/app/media/nesessary/images/{image_id}.jpg"
    if not os.path.exists(file_path):
        return jsonify({"error": "Image not found"}), 404
    return jsonify({"status": "success", "image_id": image_id, "size": os.path.getsize(file_path), "url": f"/media/nesessary/images/{image_id}.jpg"})

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(IMAGES_DIR, filename)

def is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return True

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

#     if is_private_ip(target_ip):
#         url = 'http://ip-api.com'
#     else:
#         url = f'http://ip-api.com{target_ip}?lang=ru'

#     try:
#         response = requests.get(url, timeout=3)
#         data = response.json()
#         if data.get('status') == 'success':
#             return jsonify({"status": "success", "ip": data.get('query', target_ip), "city": data.get('city', 'Неизвестный город')})
#         return jsonify({"status": "error", "message": "City not found"}), 404
#     except Exception as e:
#         return jsonify({"status": "error", "message": "Failed to resolve IP"}), 500

@app.route('/api/location', methods=['GET'])
def get_user_location():
    client_ip_from_js = request.args.get('client_ip')
    raw_x_forwarded = request.headers.get('X-Forwarded-For')
    remote_addr = request.remote_addr

    # Приоритет 1: Валидный внешний IP от клиентского JS
    if client_ip_from_js and not is_private_ip(client_ip_from_js):
        target_ip = client_ip_from_js
    # Приоритет 2: Исправленный разбор заголовка X-Forwarded-For от Nginx / Ingress
    elif raw_x_forwarded:
        # Извлекаем первый IP из цепочки и безопасно очищаем его от пробелов
        target_ip = raw_x_forwarded.split(',')[0].strip()
    # Приоритет 3: IP адрес сетевого пакета
    else:
        target_ip = remote_addr

    # Если мы запускаем локально или за роутером без DMZ, IP будет приватным (192.168.x.x или 172.x.x.x)
    # В этом случае запрашиваем внешнюю геопозицию самого сервера, чтобы эндпоинт не падал
    if is_private_ip(target_ip):
        url = 'http://ip-api.com'
    else:
        url = f'http://ip-api.com{target_ip}?lang=ru'

    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get('status') == 'success':
            return jsonify({
                "status": "success", 
                "ip": data.get('query', target_ip), 
                "city": data.get('city', 'Неизвестный город')
            })
        
        # Если ip-api вернул статус fail (например, при частых запросах)
        return jsonify({
            "status": "success", 
            "ip": target_ip, 
            "city": "Лимит запросов GeoIP"
        })
    except Exception as e:
        app.logger.error(f"Ошибка вызова внешнего GeoIP API: {e}")
        # Вместо падения 500 возвращаем статус success, но с пометкой об ошибке
        return jsonify({
            "status": "success", 
            "ip": target_ip, 
            "city": "Сервис локации временно недоступен"
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
