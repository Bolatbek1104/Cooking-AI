import os
from dotenv import load_dotenv

load_dotenv()

# Определяем путь к папке, где лежит этот файл (папка app)
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-123')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    # Создаем базу в корне проекта (на один уровень выше папки app)
    # Это гарантирует, что и создание, и чтение будут идти из одного файла
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '..', 'chef.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False