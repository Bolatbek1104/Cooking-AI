import requests
import json
from flask import current_app

def call_chef_service(ingredients):
    api_key = current_app.config['OPENROUTER_API_KEY']
    
    SYSTEM_PROMPT = (
        "Ты - злой и саркастичный шеф-повар. Твоя задача: "
        "1. Жестко высмеять пользователя за его набор ингредиентов (roast). "
        "2. Придумать реально съедобный рецепт из этого (recipe). "
        "Отвечай СТРОГО в формате JSON: "
        '{"roast": "текст унижения", "recipe": "текст рецепта", "title": "название блюда"}'
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        # ИСПОЛЬЗУЙ КОНКРЕТНУЮ МОДЕЛЬ:
        "model": "google/gemini-2.0-flash-001", 
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Мои ингредиенты: {ingredients}"}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Парсим строку в JSON
        chef_data = json.loads(content)
        
        # --- ИСПРАВЛЕНИЕ: Распаковываем список, если он пришел ---
        if isinstance(chef_data, list) and len(chef_data) > 0:
            chef_data = chef_data[0]
            
        return chef_data
        
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return {
            "roast": "Даже нейросеть в шоке от твоих запасов. Попробуй еще раз.",
            "recipe": "Рецепт невозможен.",
            "title": "Кулинарный тупик"
        }