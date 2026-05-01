from datetime import datetime
from app.models import db  # Исправленный импорт

class Recipe(db.Model):
    __tablename__ = 'recipe' # Явно укажем имя таблицы
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    title = db.Column(db.String(200))
    ingredients = db.Column(db.Text)
    roast_text = db.Column(db.Text)
    recipe_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), index=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    display_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
