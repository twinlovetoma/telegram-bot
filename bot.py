import os, json, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "Your_LTC")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "Your_SOL")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot Live"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

USERS_FILE = "users.json"
PRODUCTS_FILE = "products.json"

def load_json(file):
    if not os.path.exists(file): return {}
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return {}
def save_json(file, data):
    with open(file, 'w') as f: json.dump(f, data, indent=2)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USERS_FILE)
    uid = str(update.effective_user.id)
    if uid not in users:
        users[uid] = {"balance": 0}
        save_json(USERS_FILE, users)

    kb = [
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🛒 Browse Products", callback_data="browse"), InlineKeyboardButton("💳 My Balance", callback_data="balance")]
    ]
    if update.effective_user.id == ADMIN_ID:
        kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])

    await update.message.reply_text(f"Welcome to X STOCK!\nID: {uid}", reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = str(q.from_user.id)
    users = load_json(USERS_FILE)
    products = load_json(PRODUCTS_FILE)
    user = users.get(uid, {"balance":0})

    if data == "deposit":
        await q.edit_message_text(f"Deposit to:\nLTC: `{LTC_ADDRESS}`\nSOL: `{SOL_ADDRESS}`\n\nSend TxID after payment.", parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif data == "profile":
        await q.edit_message_text(f"👤 ID: {uid}\nBalance: ${user['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif data == "balance":
        await q.edit_message_text(f"💳 Balance: ${user['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif data == "browse":
        if not products:
            await q.edit_message_text("No products yet.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        text = "🛒 Products:\n\n"
        kb = []
        for pid, p in products.items():
            text += f"{pid}: {p['name']} - ${p['price']}\n"
            kb.append([InlineKeyboardButton(f"Buy {p['name']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("buy_"):
        pid = data.split("_")[1]
        p = products.get(pid)
        if not p: return
        if user['balance'] < p['price']:
            await q.edit_message_text(f"Insufficient balance. Need ${p['price']}, you have ${user['balance']}")
            return
        users[uid]['balance'] -= p['price']
        save_json(USERS_FILE, users)
        await q.edit_message_text(f"Purchased {p['name']}!\nRemaining Balance: ${users[uid]['balance']}")

    elif data == "back":
        kb = [
            [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
            [InlineKeyboardButton("🛒 Browse Products", callback_data="browse"), InlineKeyboardButton("💳 My Balance", callback_data="balance")]
        ]
        if q.from_user.id == ADMIN_ID:
            kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
        await q.edit_message_text(f"Welcome!\nID: {uid}", reply_markup=InlineKeyboardMarkup(kb))

    # ADMIN
    elif data == "admin":
        if q.from_user.id!= ADMIN_ID: return
        kb = [
            [InlineKeyboardButton("➕ Add Product", callback_data="admin_add")],
            [InlineKeyboardButton("💵 Add Balance to User", callback_data="admin_addbal")],
            [InlineKeyboardButton("📦 List Products", callback_data="admin_list")],
            [InlineKeyboardButton("Back", callback_data="back")]
        ]
        await q.edit_message_text("⚙️ Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

    elif data == "admin_add":
        context.user_data['awaiting'] = 'add_product'
        await q.edit_message_text("Send product in format:\n`Name | Price | Description`\nExample: Netflix 1M | 5 | 1 month warranty", parse_mode='Markdown')

    elif data == "admin_addbal":
        context.user_data['awaiting'] = 'add_balance'
        await q.edit_message_text("Send in format:\n`UserID Amount`\nExample: 7634497248 10")

    elif data == "admin_list":
        if not products: await q.edit_message_text("No products.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
        else:
            t = "\n".join([f"{k}: {v['name']} - ${v['price']}" for k,v in products.items()])
            await q.edit_message_text(f"Products:\n{t}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("Deposit TxID sent to admin. Wait for approval. Use /start")
        return

    awaiting = context.user_data.get('awaiting')
    text = update.message.text
    products = load_json(PRODUCTS_FILE)
    users = load_json(USERS_FILE)

    if awaiting == 'add_product':
        try:
            name, price, desc = [x.strip() for x in text.split("|")]
            pid = str(len(products)+1)
            products[pid] = {"name": name, "price": float(price), "desc": desc}
            save_json(PRODUCTS_FILE, products)
            await update.message.reply_text(f"Product added: {name} ID {pid}")
            context.user_data['awaiting'] = None
        except:
            await update.message.reply_text("Wrong format. Use: Name | Price | Desc")

    elif awaiting == 'add_balance':
        try:
            uid, amt = text.split()
            amt = float(amt)
            if uid not in users: users[uid] = {"balance": 0}
            users[uid]['balance'] += amt
            save_json(USERS_FILE, users)
            await update.message.reply_text(f"Added ${amt} to {uid}. New bal: ${users[uid]['balance']}")
            context.user_data['awaiting'] = None
        except:
            await update.message.reply_text("Wrong format. Use: UserID Amount")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
