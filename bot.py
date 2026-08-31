import os, json, threading, io
import qrcode
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
LTC_ADDRESS = os.getenv("LTC_ADDRESS")
SOL_ADDRESS = os.getenv("SOL_ADDRESS")

# Flask for Render
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot is Live"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

# DB
DB_FILE = "db.json"
try:
    with open(DB_FILE, 'r') as f: db = json.load(f)
except: db = {}
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)
def get_user(uid):
    uid = str(uid)
    if uid not in db: db[uid] = {"balance": 0, "refs": [], "earned": 0.0}
    return db[uid]

def make_qr(data):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("🎉 Referral", callback_data="referral")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")]
    ])

async def safe_edit(q, text, markup):
    try: await q.edit_message_text(text=text, reply_markup=markup, parse_mode='HTML')
    except BadRequest: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)
    txt = f"⚡ Welcome {user.first_name} to X STOCK! ⚡"
    if update.message:
        await update.message.reply_text(txt, reply_markup=main_kb(), parse_mode='HTML')
    else:
        await safe_edit(update.callback_query, txt, main_kb())

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    chat_id = q.message.chat_id

    if d == "deposit":
        await safe_edit(q, "💰 <b>Select Deposit Method:</b>", InlineKeyboardMarkup([
            [InlineKeyboardButton("Pay with LTC", callback_data="dep_ltc")],
            [InlineKeyboardButton("Pay with SOL", callback_data="dep_sol")],
            [InlineKeyboardButton("🔙 Back", callback_data="home")]
        ]))

    elif d == "dep_ltc":
        addr = LTC_ADDRESS
        qr_img = make_qr(addr)
        caption = f"""⚡ <b>X PREPAIDS STOCK — LTC DEPOSIT</b> ⚡

Deposit Address:
<code>{addr}</code>

Minimum Deposit: <b>0.05 LTC</b>

Send LTC to this address. Your balance will update automatically after confirmation.

⚠️ <b>WARNING:</b>
- Deposits below the minimum amount will not be processed.
- This address is valid only for your account. Do not share it.

⚠️ Note: This deposit session is only active for 30 minutes."""

        await q.message.delete()
        await context.bot.send_photo(chat_id=chat_id, photo=qr_img, caption=caption, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))

    elif d == "dep_sol":
        addr = SOL_ADDRESS
        qr_img = make_qr(addr)
        caption = f"""⚡ <b>X PREPAIDS STOCK — SOL DEPOSIT</b> ⚡

Deposit Address:
<code>{addr}</code>

Minimum Deposit: <b>0.1 SOL</b>

Send SOL to this address. Your balance will update automatically after confirmation.

⚠️ <b>WARNING:</b>
- Deposits below the minimum amount will not be processed.
- This address is valid only for your account. Do not share it.

⚠️ Note: This deposit session is only active for 30 minutes."""

        await q.message.delete()
        await context.bot.send_photo(chat_id=chat_id, photo=qr_img, caption=caption, parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="deposit")]]))

    elif d in ["home", "back_home"]:
        await q.message.delete()
        await context.bot.send_message(chat_id=chat_id, text=f"⚡ Welcome {q.from_user.first_name} to X STOCK! ⚡", reply_markup=main_kb(), parse_mode='HTML')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handler))
print("Bot polling started...")
app.run_polling()
