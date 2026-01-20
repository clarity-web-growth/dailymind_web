from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False)
    license_key = db.Column(db.String(32), nullable=True)
    subscription = db.Column(db.String(20), default="free")

    def __repr__(self):
        return f"<User {self.device_id}>"
