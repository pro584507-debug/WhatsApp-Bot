import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment Variables loaded from hosting platform
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_custom_secret_123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Verifies connection with Meta WhatsApp Developer Dashboard"""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    """Receives incoming messages from WhatsApp and sends AI replies"""
    data = request.get_json()

    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            message = messages[0]
            from_number = message["from"]
            text_body = message.get("text", {}).get("body", "")

            if text_body:
                ai_reply = get_gemini_reply(text_body)
                send_whatsapp_msg(from_number, ai_reply)
    except Exception as e:
        print(f"Error handling message: {e}")

    return jsonify({"status": "ok"}), 200

def get_gemini_reply(user_prompt):
    """Queries Gemini API for response"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}]
    }
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return "Sorry, I am having trouble connecting to AI right now."

def send_whatsapp_msg(to_number, text):
    """Posts response back to recipient on WhatsApp"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
