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
import requests
from openai import OpenAI
from models import db, User

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
MEMORY_FILE = "daily_mind_memory.json"

# ======================
# HELPERS
# ======================
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
        personality=data.get("last_personality", "Friend"),
        last_topic=data.get("last_topic", "None"),
        subscription=data.get("subscription", "free"),
    )


@app.route("/upgrade")
def upgrade():
    return render_template("upgrade.html")


@app.route("/pay")
def pay():
    # Paystack hosted payment page
    return redirect("https://paystack.shop/pay/yzthx-tqho")


@app.route("/payment-success")
def payment_success():
    reference = request.args.get("reference")

    if not reference:
        return "Invalid payment reference", 400

    headers = {
        "Authorization": f"Bearer {os.getenv('PAYSTACK_SECRET_KEY')}"
    }

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(verify_url, headers=headers)
    result = response.json()

    if result.get("status") and result["data"]["status"] == "success":
        email = result["data"]["customer"]["email"]

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, subscription="premium")
            db.session.add(user)
        else:
            user.subscription = "premium"

        db.session.commit()
        return render_template("success.html")

    return "Payment verification failed", 400


@app.route("/paystack/webhook", methods=["POST"])
def paystack_webhook():
    payload = request.get_json()

    if payload.get("event") == "charge.success":
        email = payload["data"]["customer"]["email"]

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, subscription="premium")
            db.session.add(user)
        else:
            user.subscription = "premium"

        db.session.commit()
        print("PREMIUM ACTIVATED:", email)

    return jsonify({"status": "ok"})


@app.route("/check-premium", methods=["POST"])
def check_premium():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    return jsonify({"premium": bool(user and user.subscription == "premium")})


# ======================
# CHAT STREAM (PREMIUM GATED)
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    if not user or user.subscription != "premium":
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
    app.run(debug=True)
























