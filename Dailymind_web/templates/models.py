from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    subscription = db.Column(db.String(20), default="free")
    subscription_expiry = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_premium(self):
        if self.subscription != "premium":
            return False
        if not self.subscription_expiry:
            return False
        return datetime.utcnow() <= self.subscription_expiry
