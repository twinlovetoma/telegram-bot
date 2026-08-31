import json, os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8472587455:AAHY4ktCA_nsJ2Ql2vpfnjm81ofeXZsX_h0"
ADMIN_ID = 7634497248

DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name
    if uid not in db:
        db[uid] = {"name": name, "balance": 7500.0}
        save_db(db)

    text = f"👋 Welcome {name}!\n💰 Balance: ${db[uid]['balance']:.2f}\n🆔 ID: {uid}"
    kb = [
        [InlineKeyboardButton("💰 Balance", callback_data="bal")],
        [InlineKeyboardButton("💱 Exchange Rate", callback_data="rate"), InlineKeyboardButton("📥 Deposit", callback_data="dep")],
        [InlineKeyboardButton("📤 Withdraw", callback_data="wit")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    db = load_db()
    uid = str(q.from_user.id)
    bal = db.get(uid, {}).get("balance", 0)

    if q.data == "bal":
        await q.edit_message_text(f"Your Balance: ${bal:.2f}")
    elif q.data == "rate":
        await q.edit_message_text("💱 Rate:\n1 USD = 122 BDT")
    elif q.data == "dep":
        await q.edit_message_text("📥 Deposit er jonno Admin ke knock dao")
    elif q.data == "wit":
        await q.edit_message_text("📤 Withdraw er jonno Admin ke knock dao")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(btn))

print("Bot Started! @Xprepaids")
app.run_polling()