from flask import Blueprint, request, jsonify, session
from app.services import ai_service
from app.models import db
from app.models.recipe import Recipe

# 1. СОЗДАЕМ BLUEPRINT (этой строки у тебя не хватало или она была скрыта)
bp = Blueprint('main', __name__)

@bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')

    # Достаем историю из сессии или создаем пустую
    if 'history' not in session:
        session['history'] = []

    # Вызываем сервис, передавая историю
    result = ai_service.call_chef_service(user_message, session['history'])
    
    # Добавляем в историю текущий диалог
    session['history'].append({"role": "user", "content": user_message})
    session['history'].append({"role": "assistant", "content": result['response']})
    session.modified = True 

    # Если рецепт готов, сохраняем в базу
    if result.get('stage') == 'recipe':
        new_recipe = Recipe(
            title=result.get('title', 'Chef Big Max Creation'),
            ingredients=user_message,
            recipe_text=result['response']
        )
        db.session.add(new_recipe)
        db.session.commit()

    return jsonify({
        "response": result['response'],
        "stage": result.get('stage'),
        "profile": result.get('profile'),
        "recipe_count": len(session.get('history', [])) // 2
    })