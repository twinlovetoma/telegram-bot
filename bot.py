import os, json, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "xprepaids_exchange_bot")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot Live"
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
    name=update.effective_user.first_name
    args=context.args
    if uid not in users:
        users[uid]={"balance":0,"referrals":0,"referred_by":None}
        if args and args[0]!=uid:
            ref=args[0]
            if ref in users:
                users[ref]["balance"]+=1
                users[ref]["referrals"]+=1
                users[uid]["referred_by"]=ref
        save_json(USERS_FILE,users)

    kb=[
        [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🛒 Browse", callback_data="browse"), InlineKeyboardButton("🎁 Referral", callback_data="referral")],
        [InlineKeyboardButton("💳 My Balance", callback_data="balance")]
    ]
    if update.effective_user.id==ADMIN_ID:
        kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])

    await update.message.reply_text(f"⚡ Welcome {name} to X STOCK! ⚡\nID: {uid}", reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    uid=str(q.from_user.id)
    users=load_json(USERS_FILE)
    products=load_json(PRODUCTS_FILE)
    user=users.get(uid,{"balance":0,"referrals":0})

    if q.data=="deposit":
        await q.edit_message_text("Deposit korte admin ke inbox koro. Pay er por admin balance add kore dibe.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="profile":
        await q.edit_message_text(f"👤 ID: {uid}\nBalance: ${user['balance']}\nReferrals: {user.get('referrals',0)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="balance":
        await q.edit_message_text(f"💳 Balance: ${user['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="referral":
        link=f"https://t.me/{BOT_USERNAME}?start={uid}"
        await q.edit_message_text(f"🎁 Your Referral Link:\n{link}\nPer Refer = $1\nTotal Refer: {user.get('referrals',0)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="browse":
        if not products:
            await q.edit_message_text("No products yet.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        txt="🛒 Products:\n"
        kb=[]
        for pid,p in products.items():
            txt+=f"{pid}. {p['name']} - ${p['price']}\n"
            kb.append([InlineKeyboardButton(f"Buy {p['name']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("buy_"):
        pid=q.data.split("_")[1]
        p=products.get(pid)
        if not p: return
        if user['balance'] < p['price']:
            await q.edit_message_text(f"Need ${p['price']}, you have ${user['balance']}")
            return
        users[uid]['balance']-=p['price']
        save_json(USERS_FILE,users)
        await q.edit_message_text(f"Bought {p['name']}!\nCode: {p.get('desc','Check PM')}")
    elif q.data=="back":
        kb=[
            [InlineKeyboardButton("💰 Deposit", callback_data="deposit"), InlineKeyboardButton("👤 Profile", callback_data="profile")],
            [InlineKeyboardButton("🛒 Browse", callback_data="browse"), InlineKeyboardButton("🎁 Referral", callback_data="referral")],
            [InlineKeyboardButton("💳 My Balance", callback_data="balance")]
        ]
        if q.from_user.id==ADMIN_ID:
            kb.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])
        await q.edit_message_text(f"⚡ Welcome to X STOCK! ⚡\nID: {uid}", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="admin":
        if q.from_user.id!=ADMIN_ID: return
        kb=[[InlineKeyboardButton("➕ Add Product", callback_data="admin_add")],[InlineKeyboardButton("💵 Add Balance", callback_data="admin_addbal")],[InlineKeyboardButton("📦 List Products", callback_data="admin_list")],[InlineKeyboardButton("Back", callback_data="back")]]
        await q.edit_message_text("⚙️ Admin Panel", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="admin_add":
        context.user_data['awaiting']='add_product'
        await q.edit_message_text("Format: Name | Price | Code\nEx: Netflix | 5 | code123")
    elif q.data=="admin_addbal":
        context.user_data['awaiting']='add_balance'
        await q.edit_message_text("Format: UserID Amount\nEx: 7634497248 10")
    elif q.data=="admin_list":
        txt="\n".join([f"{k}: {v['name']} - ${v['price']}" for k,v in products.items()]) if products else "No products"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))

async def msg_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID:
        await update.message.reply_text("Use /start")
        return
    awaiting=context.user_data.get('awaiting')
    if awaiting=='add_product':
        try:
            name,price,desc=[x.strip() for x in update.message.text.split("|")]
            products=load_json(PRODUCTS_FILE)
            pid=str(len(products)+1)
            products[pid]={"name":name,"price":float(price),"desc":desc}
            save_json(PRODUCTS_FILE,products)
            await update.message.reply_text(f"Added {name} ID {pid}")
            context.user_data['awaiting']=None
        except: await update.message.reply_text("Wrong format. Use: Name | Price | Code")
    elif awaiting=='add_balance':
        try:
            uid,amt=update.message.text.split()
            users=load_json(USERS_FILE)
            if uid not in users: users[uid]={"balance":0,"referrals":0}
            users[uid]["balance"]+=float(amt)
            save_json(USERS_FILE,users)
            await update.message.reply_text(f"Added ${amt} to {uid}. New: ${users[uid]['balance']}")
            context.user_data['awaiting']=None
        except: await update.message.reply_text("Wrong format. Use: UserID Amount")

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handle))
    app.run_polling()

if __name__=="__main__":
    main()
