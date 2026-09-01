import os, threading, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "TEST LIVE OK"
@flask_app.route('/health')
def health(): return "OK"

def top_menu(admin=False):
    kb = [
        [InlineKeyboardButton("📋 Listings", callback_data="list"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("⚙️ Filter", callback_data="filter")],
    ]
    if admin:
        kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

async def set_cmds(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Launch bot"),
        BotCommand("listings", "Browse"),
        BotCommand("filter", "Filter"),
        BotCommand("profile", "Profile"),
        BotCommand("balance", "Balance"),
        BotCommand("deposit", "Deposit"),
        BotCommand("vendor", "Vendor"),
        BotCommand("admin", "Admin"),
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = "🎁 WELCOME TO PREPAIDS GIFT'S 🎁\n\nBalance: $0\nStock: 142\nRefer: 10%\n\nYour premium gift card destination."
    await update.message.reply_text(txt, reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    if d == "list":
        await q.edit_message_text("📋 LISTINGS - 0 Stock\nAdd stock from Admin/Vendor", reply_markup=top_menu(q.from_user.id==ADMIN_ID))
    elif d == "profile":
        await q.edit_message_text(f"👤 PROFILE\nID: {q.from_user.id}\nBalance: $0\nVendor: Not Active", reply_markup=top_menu(q.from_user.id==ADMIN_ID))
    elif d == "deposit":
        await q.edit_message_text("💰 DEPOSIT\nLTC: ltc1q...\nSOL: So1...", reply_markup=top_menu(q.from_user.id==ADMIN_ID))
    elif d == "filter":
        await q.edit_message_text("⚙️ FILTER\nAll | Giftcard | COD 880 CP", reply_markup=top_menu(q.from_user.id==ADMIN_ID))
    elif d == "admin":
        await q.edit_message_text("👑 ADMIN PANEL\nStock:0\nAdd Stock | Add Balance | Pending COD", reply_markup=top_menu(True))
    elif d == "main":
        await q.edit_message_text("🎁 WELCOME TO PREPAIDS GIFT'S 🎁", reply_markup=top_menu(q.from_user.id==ADMIN_ID))

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).post_init(set_cmds).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    await app.initialize()
    await app.start()
    try: await app.bot.delete_webhook(drop_pending_updates=True)
    except: pass
    await app.updater.start_polling(drop_pending_updates=True)
    print("TEST LIVE")
    while True: await asyncio.sleep(3600)

def run_thread(): asyncio.run(run_bot())
if __name__ == "__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
