from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import os
import json
import hashlib
from openai import OpenAI
from dotenv import load_dotenv

from models import db, User

# ======================
# APP
# ======================
app = Flask(__name__)

# ======================
# CONFIG
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "dailymind.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SECRET_SALT = "DAILYMIND-2026-SECURE"
MEMORY_FILE = "daily_mind_memory.json"

# ======================
# DB INIT
# ======================
@app.before_first_request
def create_tables():
    db.create_all()

# ======================
# HELPERS
# ======================
def generate_license(device_id):
    raw = f"{device_id}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def is_license_valid(device_id, license_key):
    return license_key == generate_license(device_id)

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    data = load_memory()
    return render_template(
        "dashboard.html",
        conversation_count=data.get("conversation_count", 0),
        personality=data.get("last_personality", "Unknown"),
        last_topic=data.get("last_topic", "None"),
        subscription=data.get("subscription", "free"),
    )

# ======================
# CHAT STREAM
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    device_id = data.get("device_id")
    license_key = data.get("license_key")

    user = User.query.filter_by(device_id=device_id).first()

    if not user:
        user = User(device_id=device_id)
        db.session.add(user)
        db.session.commit()

    if license_key and is_license_valid(device_id, license_key):
        user.subscription = "premium"
        user.license_key = license_key
        db.session.commit()

    def generate():
        try:
            with client.responses.stream(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": f"You are DailyMind. Personality: {data.get('personality', 'Friend')}"
                    },
                    {
                        "role": "user",
                        "content": data.get("text", "")
                    }
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
        except Exception:
            yield "\n[Server stream error]\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/plain; charset=utf-8"
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)











