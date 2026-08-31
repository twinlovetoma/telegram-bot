import os, json, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

BOT_TOKEN = os.environ.get("BOT_TOKEN")
LTC_ADDRESS = os.environ.get("LTC_ADDRESS", "ltc1qYOUR_LTC_ADDRESS")
SOL_ADDRESS = os.environ.get("SOL_ADDRESS", "YOUR_SOL_ADDRESS")
STOCK_CHANNEL = os.environ.get("STOCK_CHANNEL", "https://t.me/YourStockChannel")
SUPPORT_LINK = os.environ.get("SUPPORT_LINK", "https://t.me/YourSupport")
CHECKER_BOT = os.environ.get("CHECKER_BOT", "https://t.me/YourCheckerBot")

DATA_FILE = "users.json"
def load_db():
    if os.path.exists(DATA_FILE):
        try: return json.load(open(DATA_FILE))
        except: return {}
    return {}
def save_db(db): json.dump(db, open(DATA_FILE, 'w'), indent=2)

user_db = load_db()

# Render Port Fix
web = Flask(__name__)
@web.route('/')
def home(): return "Bot Live"
threading.Thread(target=lambda: web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()

async def safe_edit(query, text, markup=None):
    try:
        await query.edit_message_text(text=text, reply_markup=markup, parse_mode='HTML')
    except BadRequest as e:
        if "Message is not modified" not in str(e): print(e)

def main_menu(bot_username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 X Checker Bot", url=CHECKER_BOT)],
        [InlineKeyboardButton("📢 Stock Updates", url=STOCK_CHANNEL), InlineKeyboardButton("💬 Refund Support", url=SUPPORT_LINK)],
        [InlineKeyboardButton("📈 Listing", callback_data='listings'), InlineKeyboardButton("🎉 Referral Program", callback_data='referral')],
        [InlineKeyboardButton("👤 Profile", callback_data='profile'), InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("❓ FAQ/News", callback_data='faq')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    args = context.args

    # Referral logic
    if uid not in user_db:
        user_db[uid] = {"balance": 0.0, "refs": [], "earned": 0.0, "active_refs": 0, "first_tx_done": False}
        # Check if joined via ref link
        if args and args[0].startswith("ref_"):
            ref_id = args[0].replace("ref_", "")
            if ref_id!= uid and ref_id in user_db:
                if uid not in user_db[ref_id]["refs"]:
                    user_db[ref_id]["refs"].append(uid)
                    save_db(user_db)

    save_db(user_db)
    bot_me = await context.bot.get_me()
    bot_username = bot_me.username

    username_show = f"@{user.username}" if user.username else user.first_name
    welcome_text = f"⚡ Welcome {username_show} to X STOCK! ⚡\n\nYour ID: <code>{uid}</code>\nBalance: ${user_db[uid]['balance']:.2f}\n\n👇 Choose an option:"

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=main_menu(bot_username), parse_mode='HTML')
    else:
        await safe_edit(update.callback_query, welcome_text, main_menu(bot_username))

async def referral_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    data = user_db.get(uid, {"refs": [], "earned": 0.0, "active_refs": 0})

    bot_me = await context.bot.get_me()
    bot_username = bot_me.username
    # EKHANE TOMAR BOT ER LINK AUTO ASBE
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"

    total_refs = len(data.get("refs", []))
    # Qualified
