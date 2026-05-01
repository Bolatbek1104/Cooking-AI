from flask import Flask
from app.models import db
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Подключаем конфиг
    from config import Config
    app.config.from_object(Config)

    # Инициализируем базу данных
    db.init_app(app)

    with app.app_context():
        # Импортируем модели ПЕРЕД create_all
        # Убедитесь, что пути к файлам именно такие
        from app.models.user import User
        from app.models.recipe import Recipe
        
        # Создаем таблицы
        db.create_all()
        print("Таблицы успешно созданы или уже существуют.")

    # Исправленный импорт Blueprint
    # Если в main.py вы назвали его bp, то импортируем bp
    from app.routes.main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    return app