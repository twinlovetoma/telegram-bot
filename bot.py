import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v30 ULTIMATE ALL FEATURE STABLE"
@flask_app.route('/health')
def health(): return "OK"

def load_file(f):
    try:
        if os.path.exists(f):
            with open(f,'r') as x: return json.load(x)
    except: pass
    return {}
def save_file(f,d):
    with open(f,'w') as x: json.dump(d,x, indent=2)
def get_user(uid):
    users=load_file("users.json"); s=str(uid)
    if s not in users: users[s]={"balance":0,"purchases":[],"ref_by":None}; save_file("users.json", users)
    return users
def premium(t): return f"╔════╗ ✨ {t} ✨ ╚════╝\n"

def main_kb(admin=False):
    kb=[
        [KeyboardButton("💳 My Balance"), KeyboardButton("👤 My Profile"), KeyboardButton("📋 Browse Cards")],
        [KeyboardButton("💰 Deposit"), KeyboardButton("💸 Withdraw"), KeyboardButton("🔍 Check Card")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("🔑 Redeem Code"), KeyboardButton("⚙️ Filter")],
        [KeyboardButton("🆘 Support"), KeyboardButton("🤖 Agent")]
    ]
    if admin: kb.append([KeyboardButton("👑 Admin Panel"), KeyboardButton("➕ Add Stock")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    o=load_file("orders.json"); pend=len([x for x in o.values() if x.get('status')=='pending'])
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Stock:{s}", callback_data="stock"), InlineKeyboardButton(f"⏳ Pend:{pend}", callback_data="orders")],[InlineKeyboardButton("➕ Add Stock", callback_data="add"), InlineKeyboardButton("📢 Post Channel", callback_data="post_all")]])

def gp_kb(ctx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'✅' if ctx.get('g',True) else '📴'}", callback_data="tg_g"), InlineKeyboardButton(f"P {'✅' if ctx.get('p',True) else '📴'}", callback_data="tg_p"), InlineKeyboardButton(f"REG {'✅' if ctx.get('reg',True) else '❌'}", callback_data="tg_reg")],
        [InlineKeyboardButton(f"Use 39%", callback_data="use_perc"), InlineKeyboardButton("Custom Price", callback_data="custom")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])

async def auto_post(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium("NEW STOCK AGENT")+"\n"
        for p in prods:
            msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅\n"
        cid=int(STOCK_CHANNEL_ID) if STOCK_CHANNEL_ID.lstrip('-').isdigit() else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; get_user(uid)
    if context.args:
        ref=str(context.args[0]); all_u=load_file("users.json"); s=str(uid)
        if s in all_u and all_u[s].get('ref_by') is None and ref!=s and ref in all_u:
            all_u[s]['ref_by']=ref; save_file("users.json", all_u)
    await update.message.reply_text(premium("WELCOME")+f"Hello {update.effective_user.first_name}!\n💎 50+ Cards | ⚡ Instant | 🤖 Agent ON\n\n👇 Choose:", reply_markup=main_kb(uid==ADMIN_ID))
    if uid==ADMIN_ID: await update.message.reply_text(premium("ADMIN"), reply_markup=admin_kb())

async def profile_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; u=get_user(uid)[str(uid)]
    await update.message.reply_text(premium("PROFILE")+f"👤 {update.effective_user.first_name}\n🆔 {uid}\n💳 ${u.get('balance',0)}\n🛒 {len(u.get('purchases',[]))}", reply_markup=main_kb(uid==ADMIN_ID))
async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; u=get_user(uid)[str(uid)]
    await update.message.reply_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}", reply_markup=main_kb(uid==ADMIN_ID))
async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text(premium("NO STOCK")+"❌ Empty! Agent checking...", reply_markup=main_kb(update.effective_user.id==ADMIN_ID)); return
    msg=premium(f"BROWSE {len(active)}")+"\n"; kb=[]
    for pid,p in active[-12:][::-1]:
        msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}\n"
        kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("⚙️ Filter", callback_data="filter")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""; uid=update.effective_user.id; low=txt.lower()
    if "/start" in txt: await start(update, context); return
    if "Profile" in txt: await profile_h(update, context); return
    if "Balance" in txt: await balance_h(update, context); return
    if "Browse" in txt: await listings_h(update, context); return
    if "Deposit" in txt: await update.message.reply_text(premium("DEPOSIT")+"LTC/SOL min $5 Agent auto check!", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Withdraw" in txt: await update.message.reply_text(premium("WITHDRAW")+"Min $10 Contact @toma", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Support" in txt: await update.message.reply_text(premium("SUPPORT")+"@toma 24/7", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Refer" in txt: await update.message.reply_text(premium("REFER")+f"Link: https://t.me/{context.bot.username}?start={uid}\nEarn 5%!", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Redeem" in txt: context.user_data['wait']="redeem"; await update.message.reply_text("🔑 Send code:"); return
    if "Filter" in txt: await update.message.reply_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("All", callback_data="list_All")],[InlineKeyboardButton("Gift Mail", callback_data="list_Gift")]])); return
    if "Agent" in txt: await update.message.reply_text(premium("AGENT")+ "✅ USD$ -> avl $ small\n✅ 39% auto\n✅ G/P/REG ✅\n✅ Channel 4 digit\n✅ Auto update", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Add Stock" in txt and uid==ADMIN_ID:
        context.user_data['wait']="add"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True
        await update.message.reply_text("Send: 451Rxxxx:xx:USD$3.39\nAgent will make avl $ small"); return
    if "Admin Panel" in txt and uid==ADMIN_ID: await update.message.reply_text(premium("ADMIN"), reply_markup=admin_kb()); return

    wait=context.user_data.get('wait')
    if wait=="add":
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
        if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
        amt=float(m.group(1)) if m else 3.39
        context.user_data['pending']=[{"code":txt, "amt":amt}]
        context.user_data['wait']="price"
        calc=round(amt*0.39,2)
        await update.message.reply_text(f"🤖 Agent detected {len(context.user_data['pending'])} card\n{txt[:4]}... avl $ {amt} -> ${calc}\nSet G/P/REG:", reply_markup=gp_kb(context.user_data)); return
    if wait=="price":
        try: sell=float(txt.replace('$','').replace('%',''))
        except: await update.message.reply_text("Send 9.75"); return
        pend=context.user_data.get('pending',[]); prods=load_file("products.json"); created=[]
        for p in pend:
            pid=str(uuid.uuid4())[:6]
            prods[pid]={"code":p['code'], "avl":f"avl $ {p['amt']}", "price":sell, "sold":False, "g":context.user_data.get('g',True), "p":context.user_data.get('p',True), "reg":context.user_data.get('reg',True)}
            created.append(prods[pid])
        save_file("products.json", prods); context.user_data['wait']=None
        await update.message.reply_text(f"✅ Added {len(created)} @ ${sell} G ✅ P ✅ REG ✅", reply_markup=main_kb(True))
        await auto_post(context, created); return
    if wait=="redeem": await update.message.reply_text("❌ Invalid"); context.user_data['wait']=None; return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data
    if d=="add": context.user_data['wait']="add"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True; await q.edit_message_text("Send: 451R...USD$3.39"); return
    if d=="cancel": await q.edit_message_text("Cancelled", reply_markup=admin_kb()); return
    if d.startswith("tg_"):
        if d=="tg_g": context.user_data['g']=not context.user_data.get('g',True)
        if d=="tg_p": context.user_data['p']=not context.user_data.get('p',True)
        if d=="tg_reg": context.user_data['reg']=not context.user_data.get('reg',True)
        await q.edit_message_reply_markup(reply_markup=gp_kb(context.user_data)); return
    if d=="use_perc":
        pend=context.user_data.get('pending',[])
        if not pend: return
        calc=round(pend[0]['amt']*0.39,2)
        prods=load_file("products.json"); created=[]
        for p in pend:
            pid=str(uuid.uuid4())[:6]
            prods[pid]={"code":p['code'], "avl":f"avl $ {p['amt']}", "price":calc, "sold":False, "g":True, "p":True, "reg":True}
            created.append(prods[pid])
        save_file("products.json", prods); context.user_data['wait']=None
        await q.edit_message_text(f"✅ Added {len(created)} @ ${calc}", reply_markup=admin_kb())
        await auto_post(context, created); return
    if d=="custom": context.user_data['wait']="price"; await q.edit_message_text("Send custom price e.g. 9.75"); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); p=load_file("products.json").get(pid)
        if not p: return
        await q.edit_message_text(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy ${p['price']}", callback_data=f"buy_{pid}")]])); return
    if d.startswith("buy_"):
        pid=d.replace("buy_",""); await q.edit_message_text(f"Confirm buy {pid}?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{pid}"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])); return
    if d.startswith("confirm_"):
        pid=d.replace("confirm_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p: return
        uid_s=str(q.from_user.id); users=load_file("users.json")
        if users.get(uid_s,{}).get('balance',0) < p['price']: await q.edit_message_text(f"❌ Need ${p['price']}"); return
        users[uid_s]['balance']-=p['price']; save_file("users.json", users)
        orders=load_file("orders.json"); oid=str(uuid.uuid4())[:6]
        orders[oid]={"buyer_id":q.from_user.id, "code":p['code'], "price":p['price'], "status":"pending", "avl":p['avl']}
        save_file("orders.json", orders)
        await q.edit_message_text(f"⏳ Order {oid} pending admin!")
        try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"NEW ORDER {oid}\nBuyer:{q.from_user.id}\n💎 {p['code'][:4]}... {p['avl']} ${p['price']}\nCode: `{p['code']}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{oid}")]]), parse_mode='Markdown')
        except: pass
        return
    if d.startswith("approve_"):
        oid=d.replace("approve_",""); orders=load_file("orders.json"); o=orders.get(oid)
        if o: o['status']="completed"; save_file("orders.json", orders)
        prods=load_file("products.json")
        for pid,pr in prods.items():
            if pr['code']==o['code']: pr['sold']=True
        save_file("products.json", prods)
        await q.edit_message_text(f"✅ {oid} Approved")
        try: await context.bot.send_message(chat_id=o['buyer_id'], text=f"✅ Approved {oid}\n🔑 `{o['code']}`", parse_mode='Markdown')
        except: pass
        return
    if d.startswith("reject_"):
        oid=d.replace("reject_",""); orders=load_file("orders.json"); o=orders.get(oid)
        if o: o['status']="rejected"; save_file("orders.json", orders); users=load_file("users.json"); b=str(o['buyer_id']); users[b]['balance']=users[b].get('balance',0)+o['price']; save_file("users.json", users)
        await q.edit_message_text(f"❌ {oid} Rejected & refunded"); return
    if d=="stock": p=load_file("products.json"); cnt=len([x for x in p.values() if not x.get('sold')]); await q.edit_message_text(f"Stock {cnt}", reply_markup=admin_kb()); return
    if d=="orders": o=load_file("orders.json"); pend=len([x for x in o.values() if x.get('status')=='pending']); await q.edit_message_text(f"Pending {pend}", reply_markup=admin_kb()); return
    if d=="post_all": prods=load_file("products.json"); active=[v for v in prods.values() if not v.get('sold')]; await auto_post(context, active[:10]); await q.edit_message_text(f"Posted {len(active[:10])}", reply_markup=admin_kb()); return

async def run_bot():
    print("BOT INIT v30 - ULTIMATE")
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ POLLING LIVE v30 - ALL FEATURE")
    while True: await asyncio.sleep(3600)

def run_thread(): asyncio.run(run_bot())

if __name__ == "__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
