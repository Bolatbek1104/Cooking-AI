from app import create_app
from app.models import db
from sqlalchemy import inspect

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # ПРИНУДИТЕЛЬНЫЙ ИМПОРТ: Это критично!
        # Без этих строк SQLAlchemy считает, что моделей не существует
        from app.models.user import User
        from app.models.recipe import Recipe
        
        print("--- ПРОВЕРКА БАЗЫ ---")
        # Создаем таблицы заново
        db.create_all()
        
        # Проверяем через инспектор
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Существующие таблицы: {tables}")
        
        if not tables:
            print("ВНИМАНИЕ: Таблицы всё еще не созданы. Проверь наследование в моделях.")
        else:
            print("УСПЕХ: База готова к работе!")
        print("----------------------")

    app.run(debug=True)