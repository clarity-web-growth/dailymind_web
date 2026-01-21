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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SECRET_SALT = "DAILYMIND-2026-SECURE"
MEMORY_FILE = "daily_mind_memory.json"

# ======================
# HELPERS
# ======================
def generate_license(seed: str) -> str:
    raw = f"{seed}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ======================
# ROUTES (UI)
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
    )

@app.route("/upgrade")
def upgrade():
    return render_template("upgrade.html")

@app.route("/pay")
def pay():
    return redirect("https://paystack.shop/pay/yzthx-tqho")

# ======================
# PAYSTACK VERIFY (AUTO-UPGRADE)
# ======================
@app.route("/payment-success")
def payment_success():
    reference = request.args.get("reference")
    if not reference:
        return "Missing payment reference", 400

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

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)

    user.subscription = "premium"
    user.license_key = license_key

    db.session.add(user)
    db.session.commit()

    return render_template("success.html")
    
@app.route("/pricing")
def pricing():
    return render_template("pricing.html")

# ======================
# CHECK PREMIUM (FRONTEND)
# ======================
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
    
@app.route("/sitemap.xml", methods=["GET"])
def sitemap():
    pages = []
    base_url = "https://dailymind-web.onrender.com"

    pages.append({
        "loc": f"{base_url}/",
        "priority": "1.0"
    })
    pages.append({
        "loc": f"{base_url}/dashboard",
        "priority": "0.9"
    })
    pages.append({
        "loc": f"{base_url}/upgrade",
        "priority": "0.8"
    })

    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'

    for page in pages:
        sitemap_xml += f"""
        <url>
            <loc>{page['loc']}</loc>
            <priority>{page['priority']}</priority>
        </url>
        """

    sitemap_xml += "</urlset>"

    return Response(sitemap_xml, mimetype="application/xml")

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
































