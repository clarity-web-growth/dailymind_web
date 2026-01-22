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
import hashlib
import requests
from datetime import date
from openai import OpenAI
from models import db, User
from flask import send_from_directory

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
# SYSTEM PROMPTS
# ======================
FREE_PROMPT = """
You are DailyMind.
Be helpful, calm, and concise.
Answer clearly but briefly.
"""

PREMIUM_PROMPT = """
You are DailyMind — a calm, intelligent personal mentor.

You do not rush.
You do not hype.
You do not judge.

Your role is not to fix the user.
Your role is to help them think clearly.

STYLE RULES:
- Speak calmly and confidently.
- Use short paragraphs.
- Avoid emojis.
- Avoid motivational clichés.
- Avoid lists unless absolutely necessary.
- Never overwhelm the user.
- Never sound like a therapist or a chatbot.

RESPONSE STRUCTURE:
1. Reflection
2. Insight
3. Guidance
4. Continuation
"""

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
    
@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(
        directory="static",
        path="sitemap.xml",
        mimetype="application/xml"
    )

# ======================
# PAYSTACK VERIFY → AUTO UPGRADE
# ======================
@app.route("/payment-success")
def payment_success():
    reference = request.args.get("reference")
    if not reference:
        return "Invalid payment reference", 400

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"

    res = requests.get(verify_url, headers=headers).json()

    if not res.get("status") or res["data"]["status"] != "success":
        return "Payment verification failed", 400

    email = res["data"]["customer"]["email"]

    user = get_or_create_user(email)
    user.subscription = "premium"
    user.license_key = generate_license(email)
    user.message_count = 0

    db.session.co



