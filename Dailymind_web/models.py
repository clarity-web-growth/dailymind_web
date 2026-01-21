from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from datetime import date

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    subscription = db.Column(db.String(20), default="free")
    message_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.Date, default=date.today)


    def activate_premium(self, days=30):
        self.subscription = "premium"
        self.subscription_expires = datetime.utcnow() + timedelta(days=days)


