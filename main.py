import os
import logging
import requests
import telebot
from urllib.parse import quote
from flask import Flask
import threading

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_KEY = os.getenv("API_KEY", "")
API_BASE_URL = "https://bio.ffutils.tech/api/update_bio"

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)


# ---------------- API CALL ----------------
def call_bio_api(token, bio):
    try:
        url = f"{API_BASE_URL}?access_token={token}&bio={quote(bio)}&key={API_KEY}"
        r = requests.get(url, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ---------------- TELEGRAM HANDLERS ----------------
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id, "👋 Bot is running on Render!")


@bot.message_handler(commands=["bio"])
def bio(msg):
    try:
        parts = msg.text.split(" ", 2)

        if len(parts) < 3:
            bot.send_message(msg.chat.id, "❌ Use: /bio <token> <bio text>")
            return

        token = parts[1]
        bio_text = parts[2]

        bot.send_message(msg.chat.id, "⏳ Updating bio...")

        result = call_bio_api(token, bio_text)

        if result.get("status") == "success":
            bot.send_message(msg.chat.id, "✅ Bio updated successfully!")
        else:
            bot.send_message(msg.chat.id, f"❌ Failed: {result.get('message')}")

    except Exception as e:
        bot.send_message(msg.chat.id, f"Error: {e}")


# ---------------- FLASK ROUTES ----------------
@app.route("/")
def home():
    return "✅ Bot is running"


@app.route("/health")
def health():
    return {"status": "ok"}


# ---------------- RUN BOTH (FIX) ----------------
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def run
