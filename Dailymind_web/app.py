from flask import Flask, request, jsonify, render_template
import os
import json
import hashlib
from datetime import datetime
from openai import OpenAI

# -------------------------
# App setup
# -------------------------
app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MEMORY_FILE = "daily_mind_memory.json"
SECRET_SALT = "DAILYMIND-2026-SECURE"

# -------------------------
# Memory helpers
# -------------------------
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {
            "conversation_count": 0,
            "last_personality": None,
            "last_topic": None,
            "subscription": "free",
            "entries": []
        }

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

# -------------------------
# License helpers
# -------------------------
def generate_license(device_id):
    raw = f"{device_id}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()


def is_license_valid(device_id, license_key):
    if not device_id or not license_key:
        return False
    return license_key.strip().upper() == generate_license(device_id)

# -------------------------
# Routes
# -------------------------
@app.route("/")
def health():
    return "DailyMind API running"


@app.route("/dashboard")
def dashboard():
    memory = load_memory()

    return render_template(
        "dashboard.html",
        conversation_count=memory.get("conversation_count", 0),
        personality=memory.get("last_personality", "Unknown"),
        last_topic=memory.get("last_topic", "None"),
        subscription=memory.get("subscription", "free")
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)

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
Personality mode: {personality}
Be calm, intelligent, concise, and human-like.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_text}
        ],
        temperature=0.8,
        max_tokens=180
    )

    reply = response.choices[0].message.content.strip()

    # ---- Save memory ----
    memory = load_memory()
    memory["conversation_count"] += 1
    memory["last_personality"] = personality
    memory["last_topic"] = "trading" if "trad" in user_text.lower() else "general"

    memory["entries"].append({
        "time": datetime.now().isoformat(),
        "text": user_text
    })

    save_memory(memory)

    return jsonify({"reply": reply})


# -------------------------
# Local run (ignored by Render)
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)


