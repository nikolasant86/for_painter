import os
import logging
from flask import Flask, jsonify, request, render_template, abort, send_from_directory
from flask_cors import CORS
from cerberus import Validator

app = Flask(__name__, template_folder='templates')
CORS(app) 

# 🌟 Настройка логирования для Flask под Gunicorn
if __name__ != '__main__':
    # Если запущен через Gunicorn, используем логгер Gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    logging.getLogger().handlers = gunicorn_logger.handlers
    logging.getLogger().setLevel(gunicorn_logger.level)
else:
    # Для локальной разработки без Gunicorn
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

PORT = int(os.environ.get("GALLERY_PORT", "8000"))
IMAGES_DIR = os.environ.get("GALLERY_IMAGES_DIR", "/app/media")

# 🌟 1. Ключи карты приведены в строгое соответствие с именами папок на сервере
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

# 🌟 2. ПОЧИНЕННЫЙ API эндпоинт (код собран в правильном порядке)
@app.route('/api/image', methods=['GET'])
def get_image_info():
    image_id = request.args.get('image_id') # Например: "terem-muhi-book/01"
    
    if not image_id:
        app.logger.warning("API call failed: Missing image_id")
        return jsonify({"error": "Missing image_id"}), 400
        
    if not v.validate({"image_id": image_id}):
        app.logger.warning(f"API call failed: Invalid image_id '{image_id}'")
        return jsonify({"error": "Invalid image_id"}), 400

    # Безопасно формируем путь к файлу на сервере
    file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")

    if not os.path.exists(file_path):
        app.logger.error(f"Image file not found: {file_path}")
        return jsonify({"error": "Image not found"}), 404

    # Возвращаем относительный URL, который обрабатывается Nginx статической папкой nesessary/images
    app.logger.info(f"Image info retrieved successfully for: {image_id}")
    return jsonify({
        "status": "success",
        "image_id": image_id,
        "size": os.path.getsize(file_path),
        "url": f"/nesessary/images/{image_id}.jpg"
    })

# Оставляем эндпоинт на случай, если картинки запрашиваются напрямую через /media/
@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(IMAGES_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
