from flask import Flask, request, Response, render_template, stream_with_context
import os, json, hashlib
from openai import OpenAI
from models import db
from flask import redirect
from models import User, db

# ======================
# APP
# ======================
app = Flask(__name__)

# ======================
# CONFIG
# ======================
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dailymind.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# 🔥 CREATE TABLES SAFELY (Flask 3 compatible)
with app.app_context():
    db.create_all()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SECRET_SALT = "DAILYMIND-2026-SECURE"
MEMORY_FILE = "daily_mind_memory.json"

# ======================
# HELPERS
# ======================
def generate_license(device_id):
    raw = f"{device_id}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

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
        subscription=data.get("subscription", "free")
    )
    
@app.route("/upgrade")
def upgrade():
    return render_template("upgrade.html")
    
@app.route("/pay")
def pay():
    PAYSTACK_URL = "https://paystack.shop/pay/yzthx-tqho"
    return redirect(PAYSTACK_URL)
    
@app.route("/success")
def payment_success():
    return render_template("success.html")
    

@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    payload = request.get_json()

    if payload.get("event") == "charge.success":
        email = payload["data"]["customer"]["email"]

        license_key = generate_license(email)

        user = User.query.filter_by(email=email).first()

        if not user:
            user = User(
                email=email,
                license_key=license_key,
                subscription="premium"
            )
            db.session.add(user)
        else:
            user.subscription = "premium"
            user.license_key = license_key

        db.session.commit()

        print("PREMIUM ACTIVATED FOR:", email)

    return jsonify({"status": "ok"})

from models import User

@app.route("/check-premium", methods=["POST"])
def check_premium():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"premium": False})

    user = User.query.filter_by(email=email).first()

    if user and user.subscription == "premium":
        return jsonify({
            "premium": True,
            "license_key": user.license_key
        })

    return jsonify({"premium": False})

# ======================
# CHAT STREAM
# ======================
email = data.get("email")

user = User.query.filter_by(email=email).first()

if not user or user.subscription != "premium":
      return Response(
        "Upgrade to Premium to continue.\n",
        content_type="text/plain"
    )

@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()

    def generate():
        try:
            with client.responses.stream(
                model="gpt-4.1-mini",
                input=[
                    {"role": "system", "content": f"You are DailyMind. Personality: {data.get('personality', 'Friend')}"},
                    {"role": "user", "content": data.get("text", "")}
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
        except Exception:
            yield "\n[Server stream error]\n"

    return Response(stream_with_context(generate()), content_type="text/plain")

# ======================
# LOCAL
# ======================
if __name__ == "__main__":
    app.run()





















