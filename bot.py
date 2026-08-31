import os, json, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "YOUR_LTC_ADDRESS")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "YOUR_SOL_ADDRESS")

CHECKER_URL = "https://t.me/XprepaidCheckerBot"
STOCK_URL = "https://t.me/YourStockChannel"
SUPPORT_URL = "https://t.me/YourSupport"

# --- Render Web Service Fix ---
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Live"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

# --- DB Fix ---
DB_FILE = "db.json"
try:
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
except:
    db = {}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f) # Ekhane age ulta chilo, etai crash er karon

def get_user(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"balance": 0, "refs": [], "earned": 0.0}
    return db[uid]

async def safe_edit(q, text, markup):
    try:
        await q.edit_message_text(text=text, reply_markup=markup, parse_mode='HTML')
    except BadRequest:
        pass

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 X Checker Bot", url=CHECKER_URL)],
        [InlineKeyboardButton("📢 Stock Updates", url=STOCK_URL), InlineKeyboardButton("🎫 Refund Support", url=SUPPORT_URL)],
        [InlineKeyboardButton("📋 Listing", callback_data="listings"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🎉 Referral Program", callback_data="referral"), InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("❓ FAQ/News", callback_data="faq")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)
    if context.args and context.args[0].startswith("ref_"):
        ref_id = context.args[0].replace("ref_","")
        if ref_id!= str(user.id) and ref_id in db:
            if str(user.id) not in db[ref_id]["refs"]:
                db[ref_id]["refs"].append(str(user.id))
                save_db()
    name = f"@{user.username}" if user.username else user.first_name
    txt = f"⚡ Welcome {name} to X STOCK! ⚡"
    if update.message:
        await update.message.reply_text(txt, reply_markup=main_kb(), parse_mode='HTML')
    else:
        await safe_edit(update.callback_query, txt, main_kb())

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    u = get_user(q.from_user.id)

    if d == "deposit":
        await safe_edit(q, "💰 <b>Select Deposit Method:</b>", InlineKeyboardMarkup([
            [InlineKeyboardButton("LTC (Litecoin)", callback_data="dep_ltc")],
            [InlineKeyboardButton("SOL (Solana)", callback_data="dep_sol")],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ]))
    elif d == "dep_ltc":
        await safe_edit(q, f"🔷 <b>LTC Deposit</b>\n\n<code>{LTC_ADDRESS}</code>", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))
    elif d == "dep_sol":
        await safe_edit(q, f"☀️ <b>SOL Deposit</b>\n\n<code>{SOL_ADDRESS}</code>", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))
    elif d == "referral":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start=ref_{q.from_user.id}"
        txt = f"🎉 <b>REFERRAL PROGRAM</b>\nInvite friends and earn $1.00 for each active referral!\n\n🔗 <b>Your unique link:</b>\n<code>{link}</code>\n\n📊 <b>Stats</b>\n- Total referrals: {len(u['refs'])}\n- Earned: ${u['earned']:.2f}\n\n❗ <b>Rules</b>\n- Bonus when referral completes first transaction\n- No self-referrals"
        await safe_edit(q, txt, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]]))
    elif d in ["home", "back_home"] or d == "listings":
        await start(update, context)
    else:
        await safe_edit(q, "Coming soon", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="home")]]))

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handler))
print("Bot polling started...")
app.run_polling()
