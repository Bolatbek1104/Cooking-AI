from flask import Blueprint, render_template, request, jsonify
from ..services.ai_service import call_chef_service
from app.models import db
from app.models.recipe import Recipe
# ВОТ ЭТА СТРОКА КРИТИЧЕСКИ ВАЖНА:
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/start', methods=['POST'])
def start():
    # Начальное приветствие от Шефа
    return jsonify({
        "response": "Ну привет. Выкладывай, что там у тебя в холодильнике, только не заставляй меня плакать от твоей нищеты.",
        "stage": "profiling"
    })

@bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    
    # Получаем ответ от ИИ
    chef_data = call_chef_service(user_msg)
    
    # СОХРАНЯЕМ В ПАМЯТЬ
    new_recipe = Recipe(
        title=chef_data.get('title'),
        ingredients=user_msg,
        roast_text=chef_data.get('roast'),
        recipe_text=chef_data.get('recipe')
    )
    db.session.add(new_recipe)
    db.session.commit()
    
    return jsonify({
    "roast": new_recipe.roast_text,
    "recipe": new_recipe.recipe_text,
    "title": new_recipe.title,
    "stage": "recipe", # Чтобы обновилась панель слева
    "recipe_count": 1
})