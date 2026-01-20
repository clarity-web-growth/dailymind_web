from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    license_key = db.Column(db.String(32), nullable=False)
    subscription = db.Column(db.String(20), default="free")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

