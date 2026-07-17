import os
import logging
from flask import Flask, jsonify, request, render_template, abort, send_from_directory
from flask_cors import CORS
from cerberus import Validator

app = Flask(__name__, template_folder='templates')
CORS(app) 

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
        abort(404)
    
    title = PROJECT_MAP[project_id]
    return render_template('project_template.html', project_name=project_id, project_title=title)

# 🌟 2. ПОЧИНЕННЫЙ API эндпоинт (код собран в правильном порядке)
@app.route('/api/image', methods=['GET'])
def get_image_info():
    image_id = request.args.get('image_id') # Например: "terem-muhi-book/01"
    
    if not image_id:
        return jsonify({"error": "Missing image_id"}), 400
        
    if not v.validate({"image_id": image_id}):
        return jsonify({"error": "Invalid image_id"}), 400

    # Безопасно формируем путь к файлу на сервере
    file_path = os.path.join(IMAGES_DIR, f"{image_id}.jpg")

    if not os.path.exists(file_path):
        return jsonify({"error": "Image not found"}), 404

    # Возвращаем относительный URL, который обрабатывается Nginx статической папкой nesessary/images
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