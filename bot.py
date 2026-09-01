import os, json, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "7634497248"))
USERNAME = os.getenv("BOT_USERNAME", "xprepaids_exchange_bot")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "OK"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))

threading.Thread(target=run_flask, daemon=True).start()

def load(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,'r', encoding='utf-8') as x: return json.load(x)
    except: return {}
def save(f,d):
    with open(f,'w', encoding='utf-8') as x: json.dump(d,x,indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json")
    uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0}
        save("users.json",users)
    kb=[
        [InlineKeyboardButton("Browse", callback_data="browse")],
        [InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Admin", callback_data="admin")]
    ]
    await update.message.reply_text("Bot Running. Price Stock different per item supported.", reply_markup=InlineKeyboardMarkup(kb))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    users=load("users.json")
    products=load("products.json")
    uid=str(q.from_user.id)

    if q.data=="browse":
        if not products:
            await q.edit_message_text("No items", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        t=""
        kb=[]
        for pid,p in products.items():
            t+=f"ID {pid} {p['name']} Price {p['price']} Stock {p['stock']} Status {p['status']}\n"
            kb.append([InlineKeyboardButton(f"Buy {p['name']} {p['price']} Stock {p['stock']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="back":
        kb=[[InlineKeyboardButton("Browse", callback_data="browse")],[InlineKeyboardButton("Balance", callback_data="balance")],[InlineKeyboardButton("Admin", callback_data="admin")]]
        await q.edit_message_text("Main Menu", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="balance":
        b=users.get(uid,{}).get("balance",0)
        await q.edit_message_text(f"Balance {b}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="admin":
        kb=[[InlineKeyboardButton("Add", callback_data="a_add")],[InlineKeyboardButton("List Edit", callback_data="a_list")],[InlineKeyboardButton("Add Balance", callback_data="a_bal")],[InlineKeyboardButton("Back", callback_data="back")]]
        await q.edit_message_text("Admin", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="a_add":
        context.user_data['w']='n'
        await q.edit_message_text("Name?")
    elif q.data=="a_list":
        if not products:
            await q.edit_message_text("No products", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
            return
        kb=[]
        t=""
        for pid,p in products.items():
            t+=f"ID {pid} {p['name']} Price {p['price']} Stock {p['stock']}\n"
            kb.append([InlineKeyboardButton(f"Edit {pid}", callback_data=f"ed_{pid}"), InlineKeyboardButton(f"Del {pid}", callback_data=f"dl_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="admin")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("ed_"):
        pid=q.data.split("_")[1]
        kb=[[InlineKeyboardButton("Price", callback_data=f"ep_{pid}")],[InlineKeyboardButton("Stock", callback_data=f"es_{pid}")],[InlineKeyboardButton("Back", callback_data="a_list")]]
        await q.edit_message_text(f"ID {pid} edit what?", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("ep_"):
        pid=q.data.split("_")[1]
        context.user_data['w']=f"ep_{pid}"
        await q.edit_message_text("New Price?")
    elif q.data.startswith("es_"):
        pid=q.data.split("_")[1]
        context.user_data['w']=f"es_{pid}"
        await q.edit_message_text("New Stock?")
    elif q.data.startswith("dl_"):
        pid=q.data.split("_")[1]
        if pid in products:
            del products[pid]
            save("products.json",products)
        await q.edit_message_text(f"Deleted {pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
    elif q.data=="a_bal":
        context.user_data['w']='bal'
        await q.edit_message_text("UserID Amount")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN: return
    w=context.user_data.get('w')
    txt=update.message.text.strip()
    prods=load("products.json")
    if w=='n':
        context.user_data['np']={"name":txt}
        context.user_data['w']='p'
        await update.message.reply_text("Price?")
    elif w=='p':
        context.user_data['np']['price']=float(txt)
        context.user_data['w']='s'
        await update.message.reply_text("Stock?")
    elif w=='s':
        context.user_data['np']['stock']=int(txt)
        context.user_data['w']='st'
        await update.message.reply_text("Status? Ex: Unregistered")
    elif w=='st':
        context.user_data['np']['status']=txt
        context.user_data['w']='wa'
        await update.message.reply_text("Warranty? Ex: 10 minutes")
    elif w=='wa':
        context.user_data['np']['warranty']=txt
        context.user_data['w']='de'
        await update.message.reply_text("Details?")
    elif w=='de':
        np=context.user_data['np']
        pid=str(len(prods)+1)
        prods[pid]={"name":np['name'],"price":np['price'],"stock":np['stock'],"status":np['status'],"warranty":np['warranty'],"details":txt}
        save("products.json",prods)
        await update.message.reply_text(f"Added ID {pid} Price {np['price']} Stock {np['stock']}")
        context.user_data['w']=None
    elif w and w.startswith("ep_"):
        pid=w.split("_")[1]
        if pid in prods:
            prods[pid]['price']=float(txt)
            save("products.json",prods)
            await update.message.reply_text(f"Price Updated {pid} to {txt}")
        context.user_data['w']=None
    elif w and w.startswith("es_"):
        pid=w.split("_")[1]
        if pid in prods:
            prods[pid]['stock']=int(txt)
            save("products.json",prods)
            await update.message.reply_text(f"Stock Updated {pid} to {txt}")
        context.user_data['w']=None
    elif w=='bal':
        try:
            uid,amt=txt.split()
            users=load("users.json")
            if uid not in users: users[uid]={"balance":0}
            users[uid]["balance"]+=float(amt)
            save("users.json",users)
            await update.message.reply_text(f"Added {amt} to {uid}")
            context.user_data['w']=None
        except: await update.message.reply_text("UserID Amount")

def main():
    if not TOKEN:
        print("BOT_TOKEN missing")
        return
    application=Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(cb))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mh))
    application.run_polling()

if __name__=="__main__":
    main()
