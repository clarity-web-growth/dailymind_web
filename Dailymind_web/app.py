from flask import (
    Flask,
    request,
    Response,
    render_template,
    stream_with_context,
    redirect,
    jsonify,
)
import os
import json
import hashlib
import requests
from datetime import date
from openai import OpenAI
from models import db, User

# ======================
# APP SETUP
# ======================
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dailymind.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ======================
# CONFIG
# ======================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SECRET_SALT = "DAILYMIND-2026-SECURE"
FREE_LIMIT = 10

# ======================
# HELPERS
# ======================
def generate_license(seed: str) -> str:
    raw = f"{seed}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def get_or_create_user(email: str) -> User:
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            subscription="free",
            message_count=0,
            last_used=date.today(),
        )
        db.session.add(user)
        db.session.commit()
    return user

# ======================
# ROUTES — UI
# ======================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

@app.route("/upgrade")
def upgrade():
    return redirect("https://paystack.shop/pay/yzthx-tqho")

# ======================
# PAYSTACK VERIFY → AUTO UPGRADE
# ======================
@app.route("/payment-success")
def payment_success():
    reference = request.args.get("reference")
    if not reference:
        return "Invalid payment reference", 400

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"
    }

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    res = requests.get(verify_url, headers=headers).json()

    if not res.get("status"):
        return "Payment verification failed", 400

    data = res["data"]
    if data["status"] != "success":
        return "Payment not successful", 400

    email = data["customer"]["email"]
    license_key = generate_license(email)

    user = get_or_create_user(email)
    user.subscription = "premium"
    user.license_key = license_key
    user.message_count = 0

    db.session.commit()

    return render_template("success.html")

# ======================
# CHECK PREMIUM (FRONTEND USE)
# ======================
@app.route("/check-premium", methods=["POST"])
def check_premium():
    email = request.json.get("email")
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
# CHAT STREAM (FREE + PREMIUM)
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    email = data.get("email")
    text = data.get("text", "")
    personality = data.get("personality", "Friend")

    if not email:
        return jsonify({"error": "Email required"}), 400

    user = get_or_create_user(email)
    today = date.today()

    # Reset daily free limit
    if user.last_used != today:
        user.message_count = 0
        user.last_used = today
        db.session.commit()

    # Enforce free limit
    if user.subscription == "free" and user.message_count >= FREE_LIMIT:
        return Response(
            "🔒 Free limit reached. Upgrade to Premium to continue.\n",
            content_type="text/plain",
            status=403,
        )

    # Count message
    user.message_count += 1
    db.session.commit()

    def generate():
        try:
            with client.responses.stream(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": f"You are DailyMind. Personality: {personality}"
                    },
                    {
                        "role": "user",
                        "content": text
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
        content_type="text/plain; charset=utf-8",
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)








































