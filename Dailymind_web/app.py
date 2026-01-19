from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import os
import json
import hashlib
from openai import OpenAI

# ======================
# APP
# ======================
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
    return (
        device_id
        and license_key
        and license_key.strip().upper() == generate_license(device_id)
    )

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

# ======================
# CHAT STREAM (CHATGPT-LIKE)
# ======================
@app.route("/chat-stream", methods=["POST"])
def chat_stream():
    data = request.get_json()

    def generate():
        try:
            with client.responses.stream(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": f"You are DailyMind. Personality: {data.get('personality', 'Friend')}"
                    },
                    {
                        "role": "user",
                        "content": data.get("text", "")
                    }
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
        except Exception as e:
            yield "\n[Server stream error]\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/plain; charset=utf-8"
    )



# ======================
# LOCAL RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)






