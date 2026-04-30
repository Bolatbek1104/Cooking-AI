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