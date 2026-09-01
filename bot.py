import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
print(f"START: TOKEN={bool(BOT_TOKEN)} ADMIN={ADMIN_ID}")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v27 ALL FEATURE FIXED - SYNTAX OK"
@flask_app.route('/health')
def health(): return "OK"

def load_file(f,d=None):
    if d is None: d={}
    try:
        if not os.path.exists(f): return d
        with open(f,'r') as x: return json.load(x)
    except: return d
def save_file(f,d):
    with open(f,'w') as x: json.dump(d, x, indent=2)
def get_cfg(): return load_file("config.json", {"perc":39,"auto_post":True})
def get_user(uid):
    users=load_file("users.json"); s=str(uid)
    if s not in users: users[s]={"balance":0,"purchases":[]}; save_file("users.json", users)
    return users
def premium(t): return f"╔════╗ ✨ {t} ✨ ╚════╝\n"

def main_kb(is_admin=False):
    kb=[[KeyboardButton("💳 My Balance"), KeyboardButton("👤 My Profile"), KeyboardButton("📋 Browse Cards")],[KeyboardButton("💰 Deposit"), KeyboardButton("⚙️ Filter"), KeyboardButton("🆘 Support")],[KeyboardButton("👥 Refer & Earn"), KeyboardButton("🔑 Redeem Code"), KeyboardButton("🤖 Agent")]]
    if is_admin: kb.append([KeyboardButton("👑 Admin Panel"), KeyboardButton("➕ Add Stock")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)

def admin_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    o=load_file("orders.json"); pend=len([x for x in o.values() if x.get('status')=='pending'])
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"Stock:{s}", callback_data="stock"), InlineKeyboardButton(f"Pend:{pend}", callback_data="orders")],[InlineKeyboardButton("Add Stock", callback_data="add"), InlineKeyboardButton("Post Channel", callback_data="post_all")]])

def gp_kb(ctx):
    c=get_cfg()
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"G {'✅' if ctx.get('g',True) else '📴'}", callback_data="tg_g"), InlineKeyboardButton(f"P {'✅' if ctx.get('p',True) else '📴'}", callback_data="tg_p"), InlineKeyboardButton(f"REG {'✅' if ctx.get('reg',True) else '❌'}", callback_data="tg_reg")],[InlineKeyboardButton(f"Use {c['perc']}%", callback_data="use_perc"), InlineKeyboardButton("Custom", callback_data="custom")],[InlineKeyboardButton("Cancel", callback_data="cancel")]])

async def set_cmds(app):
    try: await app.bot.set_my_commands([BotCommand("start","Start"),BotCommand("listings","Browse")])
    except: pass

async def auto_post_channel(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium("NEW STOCK")+"\n"
        for p in prods:
            f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
            msg+=f"💎 {f4}... {avl} ${p['sell_price']} G ✅ P ✅ REG ✅\n"
        cid=int(STOCK_CHANNEL_ID) if STOCK_CHANNEL_ID.lstrip('-').isdigit() else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; get_user(uid)
    await update.message.reply_text(premium("WELCOME")+f"Hello {update.effective_user.first_name}!\n💎 50+ Cards\n🤖 Agent ON", reply_markup=main_kb(uid==ADMIN_ID))
    if uid==ADMIN_ID: await update.message.reply_text("ADMIN", reply_markup=admin_kb())

async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text("❌ No stock", reply_markup=main_kb(update.effective_user.id==ADMIN_ID)); return
    msg=f"📋 {len(active)} CARDS\n"; kb=[]
    for pid,p in active[-10:][::-1]:
        f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
        msg+=f"💎 {f4}... {avl} ${p['sell_price']}\n"
        kb.append([InlineKeyboardButton(f"{f4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""; uid=update.effective_user.id
    if "/start" in txt: await start(update, context); return
    if "Browse" in txt: await listings_h(update, context); return
    if "Add Stock" in txt and uid==ADMIN_ID:
        context.user_data['wait']="add"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True
        await update.message.reply_text("Send: 451R...:xx:USD$3.39 USD"); return
    wait=context.user_data.get('wait')
    if wait=="add":
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
        if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
        amt=float(m.group(1)) if m else 3.39
        context.user_data['pending']=[{"code":txt, "amt":amt}]
        context.user_data['wait']="price"
        c=get_cfg(); calc=round(amt*c['perc']/100,2)
        await update.message.reply_text(f"Agent detected avl $ {amt} -> ${calc}", reply_markup=gp_kb(context.user_data)); return
    if wait=="price":
        txt2=txt.replace('$','').strip(); c=get_cfg()
        try:
            if '%' in txt2:
                perc=float(txt2.replace('%','')); c['perc']=perc; save_file("config.json", c)
                pend=context.user_data.get('pending',[]); sell=round(pend[0]['amt']*perc/100,2)
            else: sell=float(txt2)
        except: await update.message.reply_text("Send 9.75 or 39%"); return
        pend=context.user_data.get('pending',[]); prods=load_file("products.json"); created=[]
        for p in pend:
            pid=str(uuid.uuid4())[:6]; avl_small=f"avl $ {p['amt']}"
            prods[pid]={"code":p['code'], "amount":avl_small, "avl_small":avl_small, "sell_price":sell, "sold":False, "g":context.user_data.get('g',True), "p":context.user_data.get('p',True), "reg":context.user_data.get('reg',True)}
            created.append(prods[pid])
        save_file("products.json", prods)
        context.user_data['wait']=None
        await update.message.reply_text(f"✅ Added {len(created)} @ ${sell}", reply_markup=main_kb(True))
        await auto_post_channel(context, created)
        return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data
    if d=="add": context.user_data['wait']="add"; await q.edit_message_text("Send stock: 451R...USD$3.39"); return
    if d=="cancel": await q.edit_message_text("Cancelled", reply_markup=admin_kb()); return
    if d.startswith("tg_"):
        if d=="tg_g": context.user_data['g']=not context.user_data.get('g',True)
        if d=="tg_p": context.user_data['p']=not context.user_data.get('p',True)
        if d=="tg_reg": context.user_data['reg']=not context.user_data.get('reg',True)
        await q.edit_message_reply_markup(reply_markup=gp_kb(context.user_data)); return
    if d=="use_perc":
        pend=context.user_data.get('pending',[])
        if not pend: return
        c=get_cfg(); calc=round(pend[0]['amt']*c['perc']/100,2)
        prods=load_file("products.json"); created=[]
        for p in pend:
            pid=str(uuid.uuid4())[:6]; avl_small=f"avl $ {p['amt']}"
            prods[pid]={"code":p['code'], "amount":avl_small, "avl_small":avl_small, "sell_price":calc, "sold":False, "g":True, "p":True, "reg":True}
            created.append(prods[pid])
        save_file("products.json", prods)
        context.user_data['wait']=None
        await q.edit_message_text(f"✅ Added {len(created)} @ ${calc}", reply_markup=admin_kb())
        await auto_post_channel(context, created)
        return
    if d=="custom": context.user_data['wait']="price"; await q.edit_message_text("Send custom price e.g. 9.75"); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); p=load_file("products.json").get(pid)
        if not p: return
        await q.edit_message_text(f"💎 {p['code'][:4]}... {p.get('avl_small')} ${p['sell_price']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy ${p['sell_price']}", callback_data=f"buy_{pid}")]])); return
    if d.startswith("buy_"): await q.edit_message_text("✅ Pending admin"); return
    if d=="stock": p=load_file("products.json"); cnt=len([x for x in p.values() if not x.get('sold')]); await q.edit_message_text(f"Stock {cnt}", reply_markup=admin_kb()); return
    if d=="post_all":
        prods=load_file("products.json"); active=[v for v in prods.values() if not v.get('sold')]
        await auto_post_channel(context, active[:10])
        await q.edit_message_text(f"Posted {len(active[:10])}", reply_markup=admin_kb()); return

async def run_bot_async():
    app = Application.builder().token(BOT_TOKEN).post_init(set_cmds).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("listings", listings_h))
    app.add_handler(CallbackQueryHandler(cb_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    print("BOT INIT v27")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ BOT POLLING LIVE v27 FIXED")
    await app.updater.idle()

def run_bot_thread(): asyncio.run(run_bot_async())

if __name__ == "__main__":
    threading.Thread(target=run_bot_thread, daemon=True).start()
    port = int(os.getenv("PORT", 10000))
    print(f"Flask bind 0.0.0.0:{port}")
    flask_app.run(host='0.0.0.0', port=port)
