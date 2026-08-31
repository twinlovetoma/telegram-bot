    import os, threading, json
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "YOUR_LTC_ADDRESS")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "YOUR_SOL_ADDRESS")
CHECKER_BOT = os.getenv("CHECKER_BOT", "https://t.me/YourCheckerBot")
STOCK_CHANNEL = os.getenv("STOCK_CHANNEL", "https://t.me/YourStockChannel")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/YourSupport")

# Render Fix
web = Flask(__name__)
@web.route('/')
def home(): return "Bot Live"
threading.Thread(target=lambda: web.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

# DB
DB_FILE = "db.json"
try: db = json.load(open(DB_FILE))
except: db = {}

def save_db(): json.dump(db, open(DB_FILE, 'w'))

async def safe_edit(q, text, markup=None):
    try: await q.edit_message_text(text, markup, parse_mode='HTML')
    except BadRequest as e:
        if "not modified" not in str(e).lower(): print(e)

def get_user(uid):
    uid=str(uid)
    if uid not in db: db[uid]={"balance":0,"refs":[],"earned":0,"active_refs":0}
    return db[uid]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_user(user.id)

    # Referral handle
    if context.args and context.args[0].startswith("ref_"):
        ref_id = context.args[0].replace("ref_","")
        if ref_id!= str(user.id) and ref_id in db and str(user.id) not in db[ref_id]["refs"]:
            db[ref_id]["refs"].append(str(user.id))
            save_db()

    username = f"@{user.username}" if user.username else user.first_name
    bot_me = await context.bot.get_me()

    text = f"⚡ Welcome {username} to X STOCK! ⚡\n\nYour one stop for premium stocks."

    keyboard = [
        [InlineKeyboardButton("🤖 X Checker Bot", url=CHECKER_BOT)],
        [InlineKeyboardButton("📢 Stock Updates", url=STOCK_CHANNEL), InlineKeyboardButton("🎫 Refund Support", url=SUPPORT_CHANNEL)],
        [InlineKeyboardButton("📋 Listing", callback_data='listings'), InlineKeyboardButton("👤 Profile", callback_data='profile')],
        [InlineKeyboardButton("🎉 Referral Program", callback_data='referral'), InlineKeyboardButton("💰 Deposit", callback_data='deposit')],
        [InlineKeyboardButton("❓ FAQ/News", callback_data='faq')]
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await safe_edit(update.callback_query, text, InlineKeyboardMarkup(keyboard))

async def referral_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    u = get_user(user.id)
    bot_me = await context.bot.get_me()
    link = f"https://t.me/{bot_me.username}?start=ref_{user.id}"

    # Ekhane tomar bot er link e thakbe, 100% dynamic
    text = f"""🎉 <b>REFERRAL PROGRAM</b>
Invite friends and earn $1.00 for each active referral!

🔗 <b>Your unique link:</b>
<code>{link}</code>

📊 <b>Stats</b>
• Total referrals: {len(u['refs'])}
• Earned: ${u['earned']:.2f}

❗ <b>Rules</b>
- Bonus awarded when referral completes first transaction
- No self-referrals
- Fraudulent referrals will be banned"""

    await safe_edit(q, text, InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back')]]))

async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await safe_edit(q, "💰 <b>Select Deposit Method:</b>", InlineKeyboardMarkup([
        [InlineKeyboardButton("LTC (Litecoin)", callback_data='dep_ltc')],
        [InlineKeyboardButton("SOL (Solana)", callback_data='dep_sol')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ]))

async def show_ltc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    await safe_edit(q, f"🔷 <b>LTC Deposit</b>\n\nSend LTC to:\n<code>{LTC_ADDRESS}</code>\n\nMin $5", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='deposit')]]))

async def show_sol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    await safe_edit(q, f"☀️ <b>SOL Deposit</b>\n\nSend SOL to:\n<code>{SOL_ADDRESS}</code>\n\nMin $5", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='deposit')]]))

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=update.callback_query.data
    if data=='referral': await referral_menu(update, context)
    elif data=='deposit': await deposit_menu(update, context)
    elif data=='dep_ltc': await show_ltc(update, context)
    elif data=='dep_sol': await show_sol(update, context)
    elif data=='back': await start(update, context)
    elif data=='profile':
        u=get_user(update.callback_query.from_user.id)
        await safe_edit(update.callback_query, f"👤 ID: {update.callback_query.from_user.id}\nBalance: ${u['balance']}", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back')]]))
    else:
        await safe_edit(update.callback_query, "Coming soon...", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back')]]))

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
print("Bot polling started..."); app.run_polling()
