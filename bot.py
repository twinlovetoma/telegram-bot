import os, json, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "xprepaids_exchange_bot")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Gift Mail Bot Live"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

USERS_FILE="users.json"
PRODUCTS_FILE="products.json"

def load_json(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,'r') as file: return json.load(file)
    except: return {}
def save_json(f,d):
    with open(f,'w') as file: json.dump(d,file,indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load_json(USERS_FILE)
    uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0,"referrals":0}
        save_json(USERS_FILE,users)
    kb=[
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🛒 Browse Gifts", callback_data="browse"), InlineKeyboardButton("🎁 Referral", callback_data="referral")],
        [InlineKeyboardButton("💳 My Balance", callback_data="balance")]
    ]
    if update.effective_user.id==ADMIN_ID:
        kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
    await update.message.reply_text(f"⚡ Welcome {update.effective_user.first_name}!\n\nProduct Type: giftscardsmail\nReady to sell ✅", reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    uid=str(q.from_user.id)
    users=load_json(USERS_FILE)
    products=load_json(PRODUCTS_FILE)

    if q.data=="back":
        kb=[
            [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
            [InlineKeyboardButton("🛒 Browse Gifts", callback_data="browse"), InlineKeyboardButton("🎁 Referral", callback_data="referral")],
            [InlineKeyboardButton("💳 My Balance", callback_data="balance")]
        ]
        if q.from_user.id==ADMIN_ID: kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
        await q.edit_message_text("⚡ Main Menu ⚡", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="browse":
        if not products:
            await q.edit_message_text("No products yet. Admin theke add koro.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        txt="🛒 **Available Stock**\n\n"
        kb=[]
        for pid,p in products.items():
            txt+=f"**ID {pid}**\nProduct: {p['name']}\nPrice: ${p['price']} | Stock: {p['stock']}\nStatus: {p['status']} | Warranty: {p['warranty']}\n---\n"
            kb.append([InlineKeyboardButton(f"Buy {p['name']} - ${p['price']} (Stock {p['stock']})", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif q.data.startswith("buy_"):
        pid=q.data.split("_")[1]
        p=products.get(pid)
        await q.edit_message_text(f"Product: {p['name']}\nPrice: ${p['price']} | Stock: {p['stock']}\nStatus: {p['status']}\nWarranty: {p['warranty']}\nDetails: [Full details only after purchase]", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm Buy", callback_data=f"confirm_{pid}")],[InlineKeyboardButton("Back", callback_data="back")]]))

    elif q.data.startswith("confirm_"):
        pid=q.data.split("_")[1]
        p=products.get(pid)
        user=users.get(uid,{"balance":0})
        if user["balance"] < float(p["price"]):
            await q.edit_message_text(f"❌ Balance kom. Dorkar ${p['price']}, ache ${user['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        users[uid]["balance"]-=float(p["price"])
        products[pid]["stock"]=int(products[pid]["stock"])-1
        if products[pid]["stock"]<=0: del products[pid]
        save_json(USERS_FILE,users)
        save_json(PRODUCTS_FILE,products)
        await q.edit_message_text(f"✅ Purchased!\n\nProduct: {p['name']}\nPrice: ${p['price']}\nDetails: {p['details']}\nWarranty: {p['warranty']} support time", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif q.data=="admin":
        kb=[[InlineKeyboardButton("➕ Add New Mail", callback_data="admin_add")],[InlineKeyboardButton("📋 List / Edit / Delete", callback_data="admin_list")],[InlineKeyboardButton("💵 Add Balance", callback_data="admin_addbal")],[InlineKeyboardButton("Back", callback_data="back")]]
        await q.edit_message_text("⚙️ Admin Panel - Sob kichu ekhan theke change korte parba", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="admin_add":
        context.user_data['awaiting']='add_name'
        await q.edit_message_text("1️⃣ Product Name? Ex: giftscardsmail")

    elif q.data=="admin_list":
        if not products:
            await q.edit_message_text("No products", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
            return
        kb=[]
        txt="📋 Sob Item
