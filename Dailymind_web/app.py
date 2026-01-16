from flask import Flask, request, jsonify, render_template
import os
import json
import hashlib
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)

# ======================
# CONFIG
# ======================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SECRET_SALT = "DAILYMIND-2026-SECURE"
MEMORY_FILE = "daily_mind_memory.json"

# ======================
# HELPERS
# ======================
def generate_license(device_id):
    raw = f"{device_id}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def is_license_valid(device_id, license_key):
    if not device_id or not license_key:
        return False
    return license_key.strip().upper() == generate_license(device_id)

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ======================
# ROUTES
# ======================
@app.route("/")
def health():
    return "DailyMind API running"

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

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    user_text = data.get("text", "")
    personality = data.get("personality", "Friend")
    device_id = data.get("device_id")
    license_key = data.get("license_key")

    if not is_license_valid(device_id, license_key):
        return jsonify({
            "error": "FORBIDDEN",
            "message": "Upgrade to DailyMind Premium to continue using AI."
        }), 403

    system_prompt = f"""
You are DailyMind.
Personality: {personality}

RULES:
- Respond calmly and intelligently
- Always finish your thoughts
- Structure long answers clearly
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.8,
        max_tokens=300
    )

    reply = response.choices[0].message.content.strip()

    return jsonify({"reply": reply})


# -------------------------
# Local run (ignored by Render)
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)




