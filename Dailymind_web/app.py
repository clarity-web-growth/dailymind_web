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

Your role is not to solve problems, but to help the user think more clearly.

RULES:
- Speak calmly and confidently.
- Use short paragraphs.
- No emojis.
- No hype.
- No clichés.
- Never rush the user.

STRUCTURE EVERY RESPONSE:

1. Reflection  
Briefly reflect the emotional or mental state behind what the user said.
Do not repeat their words. Show understanding.

2. Insight  
Explain what might be happening beneath the surface.
Name the tension, pattern, or confusion gently.

3. One Direction  
Offer ONE grounded perspective or step.
Not multiple options.

4. Continuation  
End by inviting depth, not closing the topic.
Use calm prompts like:
- “Do you want to explore this further?”
- “We can slow this down if you want.”
- “Would you like to look at this from another angle?”

IMPORTANT:
- If the user sounds overwhelmed, slow the pace.
- If the user sounds confused, simplify.
- If the user sounds emotional, acknowledge before guiding.
- Never try to fix everything at once.

Clarity over completeness.
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

    user = get_or_create_user(email)
    user.subscription = "premium"
    user.license_key = generate_license(email)
    user.message_count = 0

    db.session.commit()

    return render_template("success.html")

# ======================
# CHECK PREMIUM
# ======================
@app.route("/check-premium", methods=["POST"])
def check_premium():
    email = request.json.get("email")
    user = User.query.filter_by(email=email).first()

    return jsonify({
        "premium": bool(user and user.subscription == "premium")
    })

# ======================
# CHAT STREAM
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    email = data.get("email")
    text = data.get("text", "")
    personality = data.get("personality", "Friend")
    
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

RESPONSE STRUCTURE (MANDATORY):

1️⃣ Reflection  
Begin by reflecting the essence of what the user is experiencing.  
Do not repeat their words verbatim.  
Show understanding in one or two sentences.

2️⃣ Insight  
Explain what may be happening beneath the surface.  
Name the tension, pattern, or conflict if there is one.  
Be honest, but gentle.

3️⃣ Guidance  
Offer ONE grounded perspective or direction.  
Not multiple steps. Not a checklist.  
One clear reframe or action.

4️⃣ Continuation  
End by inviting depth, not closure.  
Use calm prompts like:
- “We can slow this down if you want.”
- “Would you like to explore this further?”
- “Do you want to look at this from another angle?”

EMOTIONAL AWARENESS:
- If the user sounds overwhelmed, slow the pace.
- If the user sounds confused, simplify.
- If the user sounds emotional, acknowledge before guiding.
- If the user sounds stuck, reduce the problem to something manageable.

MEMORY BEHAVIOR:
- If context exists, gently reference it.
- Never mention logs, dates, or system memory.
- Use phrases like: “You’ve touched on something similar before.”

GOAL:
Leave the user feeling:
- understood
- calmer
- clearer
- capable of thinking on their own

Clarity matters more than completeness.

    if not email:
        return jsonify({"error": "Email required"}), 400

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
            "🔒 Free limit reached. Upgrade to Premium.\n",
            status=403,
            content_type="text/plain",
        )

    user.message_count += 1
    db.session.commit()

    system_prompt = PREMIUM_PROMPT if user.subscription == "premium" else FREE_PROMPT

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
        except Exception:
            yield "\n[Server error]\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/plain; charset=utf-8",
    )

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)












































