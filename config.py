import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# Определяем путь к папке, где лежит этот файл (папка app)
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-123')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
    
    # Создаем базу в корне проекта (на один уровень выше папки app)
    # Это гарантирует, что и создание, и чтение будут идти из одного файла
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///' + os.path.join(basedir, 'chef.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
