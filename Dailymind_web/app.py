from flask import (
    Flask,
    request,
    Response,
    render_template,
    stream_with_context,
    redirect,
    jsonify,
    send_from_directory,
)
import os
import hashlib
import requests
from datetime import date
from openai import OpenAI
from models import db, User
from sqlalchemy import func

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
You are DailyMind — a calm private mentor.

You do not give hype advice.
You do not give motivational speeches.
You do not give bullet lists unless absolutely required.
You do not overwhelm the user.

Your role is to help the user think clearly.

STYLE RULES (Non-negotiable):
- Short paragraphs only.
- No emojis.
- No exclamation marks.
- No numbered lists unless explicitly requested.
- No generic internet advice.
- No “here are some tips” phrasing.
- No teaching tone.

Response structure:
1. Reflect what you observe.
2. Offer one clear insight.
3. Suggest one grounded action.
4. End with a calm continuation question.

If the user asks about trading:
- Focus on discipline and decision quality.
- Do not give strategy lists.
- Do not give step-by-step instructions.
- Guide reflection instead of instruction.

DailyMind speaks only when it adds stability.
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


@app.route("/blog")
def blog():
    return render_template("blog.html")

@app.route("/blog/<slug>")
def blog_post(slug):
    try:
        return render_template(f"blog/{slug}.html")
    except:
        return "Blog post not found", 404

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(
        directory="static",
        path="sitemap.xml",
        mimetype="application/xml",
    )

# ======================
# CHECK PREMIUM (FRONTEND)
# ======================
@app.route("/check-premium", methods=["POST"])
def check_premium():
    email = request.json.get("email")
    user = User.query.filter_by(email=email).first()

    return jsonify({
        "premium": bool(user and user.subscription == "premium")
    })

# ======================
# CHAT STREAM (FREE + PREMIUM)
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    email = data.get("email")
    text = data.get("text", "").strip()

    if not email:
        return jsonify({"error": "Email required"}), 400

    if not text:
        return jsonify({"error": "Message required"}), 400

    user = get_or_create_user(email)
    today = date.today()

    # Reset daily limit
    if user.last_used != today:
        user.message_count = 0
        user.last_used = today
        db.session.commit()

    # Enforce free limit
    if user.subscription == "free" and user.message_count >= FREE_LIMIT:
        return Response(
            "You’ve reached today’s free limit. Upgrade to continue.",
            status=403,
            content_type="text/plain",
        )

    user.message_count += 1
    db.session.commit()

    system_prompt = (
        PREMIUM_PROMPT if user.subscription == "premium" else FREE_PROMPT
    )

    def generate():
        try:
            with client.responses.stream(
                model="gpt-4.1-mini",
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
        except Exception as e:
            print("OpenAI error:", e)
            yield "I’m having trouble responding right now. Please try again."

    return Response(
        stream_with_context(generate()),
        content_type="text/plain; charset=utf-8",
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

    db.session.commit()

    return render_template("success.html")

# ======================
# RUN (LOCAL ONLY)
# ======================
if __name__ == "__main__":
    app.run(debug=True)

# ======================
# ADMIN DASHBOARD
# ======================
@app.route("/admin")
def admin_dashboard():
    today = date.today()

    total_users = User.query.count()
    premium_users = User.query.filter_by(subscription="premium").count()
    free_users = User.query.filter_by(subscription="free").count()

    total_messages = db.session.query(
        func.sum(User.message_count)
    ).scalar() or 0

    users_today = User.query.filter_by(last_used=today).count()

    recent_users = User.query.order_by(User.id.desc()).limit(10).all()

    return render_template(
        "admin.html",
        total_users=total_users,
        premium_users=premium_users,
        free_users=free_users,
        total_messages=total_messages,
        users_today=users_today,
        recent_users=recent_users,
    )








