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
from openai import OpenAI
from models import db, User
from datetime import datetime

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

with app.app_context():
    db.create_all()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PAYMENT_URL = "https://paystack.shop/pay/yzthx-tqho"

SECRET_SALT = "DAILYMIND-2026-SECURE"
MEMORY_FILE = "daily_mind_memory.json"

# ======================
# HELPERS
# ======================
def generate_license(email: str) -> str:
    raw = f"{email}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def enforce_subscription(user):
    if not user:
        return False

    if user.subscription != "premium":
        return False

    if not user.subscription_expires:
        return False

    if user.subscription_expires < datetime.utcnow():
        user.subscription = "free"
        db.session.commit()
        return False

    return True


# ======================
# ROUTES
# ======================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    email = request.args.get("email")
    user = User.query.filter_by(email=email).first()

    if not user:
        return redirect("/upgrade")

    expires = (
        user.subscription_expires.strftime("%Y-%m-%d")
        if user.subscription_expires
        else "N/A"
    )

    return render_template(
        "dashboard.html",
        email=user.email,
        plan=user.subscription,
        expires=expires,
        license_key=user.license_key,
    )

@app.route("/upgrade")
def upgrade():
    return render_template("upgrade.html")

@app.route("/pay")
def pay():
    return redirect(PAYSTACK_PAYMENT_URL)

@app.route("/payment-success")
def payment_success():
    reference = request.args.get("reference")
    if not reference:
        return "Missing reference", 400

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
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

   user = User.query.filter_by(email=email).first()

if not user:
       user = User(email=email)
       db.session.add(user)

       user.activate_premium(days=30)
       user.license_key = generate_license(email)
       db.session.commit()
    return render_template("success.html")

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
            "license_key": user.license_key,
        })

    return jsonify({"premium": False})

# ======================
# CHAT STREAM (PREMIUM GATED)
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    if not enforce_subscription(user):
        return Response(
            "Upgrade to Premium to continue.\n",
            content_type="text/plain",
        )

    def generate():
        try:
            with client.responses.stream(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": f"You are DailyMind. Personality: {data.get('personality', 'Friend')}",
                    },
                    {
                        "role": "user",
                        "content": data.get("text", ""),
                    },
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
        except Exception:
            yield "\n[Server stream error]\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/plain",
    )

# ======================
# LOCAL
# ======================
if __name__ == "__main__":
    app.run()





























