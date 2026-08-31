import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- TOMAR LINK GULO EKANE ---
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1q-your-ltc-address-here")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "SoL-your-sol-address-here")
CHECKER_BOT_URL = "https://t.me/XprepaidCheckerBot"
STOCK_CHANNEL_URL = "https://t.me/YourStockChannel"
SUPPORT_URL = "https://t.me/YourSupport"

# Render er port fix
web = Flask(__name__)
@web.route('/')
def home(): return "Bot is Live"
def run_flask():
    web.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
threading.Thread(target=run_flask, daemon=True).start()

# --- DB ---
DB_FILE = "db.json"
try: db = json.load(open(DB_FILE))
except: db = {}
def save_db(): json.dump(db, open(DB_FILE, 'w'))
def get_user(uid):
    uid=str(uid)
    if uid not in db:
        db[uid] = {"balance":0, "refs":[], "earned":0.0}
    return db[uid]

# --- SAFE EDIT (Ei function tai error fix korbe) ---
async def safe_edit(query, text, markup=None):
    try:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode='HTML')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            print(f"Edit Error: {e}")

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 X Checker Bot", url=CHECKER_BOT_URL)],
        [InlineKeyboardButton("📢 Stock Updates",
