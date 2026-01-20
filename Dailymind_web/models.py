from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    subscription = db.Column(db.String(20), default="free")
    license_key = db.Column(db.String(32))
    subscription_expires = db.Column(db.DateTime)

    def activate_premium(self, days=30):
        self.subscription = "premium"
        self.subscription_expires = datetime.utcnow() + timedelta(days=days)


