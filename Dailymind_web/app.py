from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")
from flask import Flask, request, jsonify
import hashlib
import os
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SECRET_SALT = "DAILYMIND-2026-SECURE"

def generate_license(device_id):
    raw = f"{device_id}-{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()

def is_license_valid(device_id, license_key):
    if not device_id or not license_key:
        return False
    return license_key.strip().upper() == generate_license(device_id)


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
You are DailyMind – calm, intelligent, human-like.
Personality mode: {personality}
Respond naturally and concisely.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.8,
        max_tokens=180
    )

    reply = response.choices[0].message.content.strip()
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run()




