import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
STOCK_CHANNEL_LINK = os.getenv("STOCK_CHANNEL_LINK", "https://t.me/your_stock_channel")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1q...")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "So1...")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v34 ADMIN RESTORED"
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
    if s not in users: users[s]={"balance":0,"purchases":[],"is_vendor":False,"vendor_sales":0,"ref_by":None,"requests_vendor":False}; save_file("users.json", users)
    return users
def get_cfg(): return load_file("config.json", {"perc":39,"comm":5})
def premium(t): return f"╔════╗ ✨ {t} ✨ ╚════╝\n"

def top_menu(admin=False):
    kb=[
        [InlineKeyboardButton("📋 Listings", callback_data="top_list"), InlineKeyboardButton("💳 Balance", callback_data="top_bal"), InlineKeyboardButton("👤 Profile", callback_data="top_profile")],
        [InlineKeyboardButton("💰 Deposit", callback_data="top_dep"), InlineKeyboardButton("⚙️ Filter", callback_data="top_filter"), InlineKeyboardButton("🔍 Check", callback_data="top_check")],
        [InlineKeyboardButton("👥 Refer", callback_data="top_ref"), InlineKeyboardButton("🔑 Redeem", callback_data="top_redeem"), InlineKeyboardButton("🏪 Vendor", callback_data="top_vendor")],
        [InlineKeyboardButton("🆘 Support", callback_data="top_sup"), InlineKeyboardButton("↩️ Refund Rule", callback_data="top_refund"), InlineKeyboardButton("📢 Stock", callback_data="top_channel")],
    ]
    if admin: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="top_admin")])
    return InlineKeyboardMarkup(kb)

# EXACT ADMIN PANEL FROM YOUR SCREENSHOT
def admin_panel_kb():
    cfg=get_cfg(); prods=load_file("products.json"); stock=len([x for x in prods.values() if not x.get('sold')])
    # Perc: 65% etc will be in message text, here only buttons
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Stock", callback_data="add_stock"), InlineKeyboardButton("💲 Set %", callback_data="set_perc")],
        [InlineKeyboardButton("💵 Add Balance", callback_data="add_bal"), InlineKeyboardButton("🔄 Relist", callback_data="relist_admin")],
        [InlineKeyboardButton("🧑‍💼 Vendor Req", callback_data="vendor_req"), InlineKeyboardButton("👥 All Sellers", callback_data="all_sellers")],
        [InlineKeyboardButton("⏳ Pending Orders", callback_data="orders"), InlineKeyboardButton("📊 Sales History", callback_data="sales_hist")],
        [InlineKeyboardButton("📦 Buyer History", callback_data="buyer_hist")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ])

def welcome_text():
    cfg=get_cfg()
    return (
        premium("WELCOME TO PREPAIDS GIFT'S")+
        "Hello! 👋\n💎 50+ Cards | ⚡ Instant | 🤖 Agent ON\n\n"
        "📋 /listings - Browse\n💳 /balance - Balance\n💰 /deposit - LTC/SOL\n⚙️ /filter - Filter\n🔍 /check - Check Card\n"
        "👤 /profile - Profile + History + Relist\n🏪 /vendor - Vendor Dash\n\n"
        "↩️ REFUND RULE:\n• Invalid = Full refund 10 min\n• Valid used = No refund\n• Proof needed\n\n"
        f"📢 Stock: {STOCK_CHANNEL_LINK}\n🆘 /support @toma 24/7\n"
        f"Perc: {cfg.get('perc',39)}% | Comm: {cfg.get('comm',5)}%\n\n"
        "👇 Top buttons (no bottom keyboard):"
    )

def admin_panel_text():
    cfg=get_cfg(); prods=load_file("products.json"); stock=len([x for x in prods.values() if not x.get('sold')])
    return (
        premium("ADMIN PANEL")+
        f"👑 Admin Panel\nPerc: {cfg.get('perc',39)}%\nComm: {cfg.get('comm',5)}%\nStock: {stock}\n\n"
        "Choose action:"
    )

async def set_cmds(app):
    cmds=[
        BotCommand("start","🏠 Welcome + Rules"), BotCommand("listings","📋 Browse"), BotCommand("balance","💳 Balance"),
        BotCommand("deposit","💰 Deposit"), BotCommand("filter","⚙️ Filter"), BotCommand("check","🔍 Check"),
        BotCommand("profile","👤 Profile"), BotCommand("vendor","🏪 Vendor"), BotCommand("support","🆘 Support"),
        BotCommand("admin","👑 Admin Panel"),
    ]
    try: await app.bot.set_my_commands(cmds)
    except: pass

async def auto_post(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium("NEW STOCK")+"\n"
        for p in prods: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅\n"
        cid=int(STOCK_CHANNEL_ID) if STOCK_CHANNEL_ID.lstrip('-').isdigit() else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    await update.message.reply_text(welcome_text(), reply_markup=top_menu(update.effective_user.id==ADMIN_ID), disable_web_page_preview=True)

async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text(premium("NO STOCK"), reply_markup=top_menu(update.effective_user.id==ADMIN_ID)); return
    msg=premium(f"LISTINGS {len(active)}")+"\n"; kb=[]
    for pid,p in active[-10:][::-1]: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}\n"; kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("🏠 Main", callback_data="main_menu")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)[str(update.effective_user.id)]
    await update.message.reply_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
async def deposit_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("DEPOSIT")+"Choose:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]]))
async def filter_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎁 Gift", callback_data="filter_gift"), InlineKeyboardButton("All", callback_data="filter_all")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]]))
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    await update.message.reply_text(admin_panel_text(), reply_markup=admin_panel_kb())

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""; uid=update.effective_user.id; low=txt.lower()
    if "/start" in txt: await start(update, context); return
    if "/balance" in txt: await balance_h(update, context); return
    if "/listings" in txt or "/listing" in txt: await listings_h(update, context); return
    if "/deposit" in txt: await deposit_h(update, context); return
    if "/filter" in txt: await filter_h(update, context); return
    if "/admin" in txt: await admin_cmd(update, context); return

    wait=context.user_data.get('wait')
    if wait=="add_stock":
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
        if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
        amt=float(m.group(1)) if m else 3.39
        context.user_data['pending']=txt; context.user_data['amt']=amt; context.user_data['wait']="set_price"
        cfg=get_cfg(); calc=round(amt*cfg['perc']/100,2)
        await update.message.reply_text(f"Detected avl $ {amt} -> ${calc} (Perc {cfg['perc']}%)\nSend custom price or /useperc", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Use {cfg['perc']}% (${calc})", callback_data="use_perc"), InlineKeyboardButton("Custom", callback_data="custom_price")]])); return
    if wait=="set_price":
        try: price=float(txt.replace('$',''))
        except: await update.message.reply_text("Send price e.g. 9.75"); return
        pid=str(uuid.uuid4())[:6]; prods=load_file("products.json")
        prods[pid]={"code":context.user_data['pending'], "avl":f"avl $ {context.user_data['amt']}", "price":price, "sold":False, "owner":uid}
        save_file("products.json", prods); context.user_data['wait']=None
        await update.message.reply_text(f"✅ Added {pid} ${price} G ✅ P ✅ REG ✅", reply_markup=admin_panel_kb())
        await auto_post(context, [prods[pid]]); return
    if wait=="add_bal":
        try:
            parts=txt.split(); uid_t=parts[0]; amt=float(parts[1])
            users=load_file("users.json")
            if uid_t in users: users[uid_t]['balance']=users[uid_t].get('balance',0)+amt; save_file("users.json", users); await update.message.reply_text(f"✅ Added ${amt} to {uid_t}", reply_markup=admin_panel_kb())
            else: await update.message.reply_text("User not found", reply_markup=admin_panel_kb())
        except: await update.message.reply_text("Format: USERID AMOUNT\nEx: 7634497248 50", reply_markup=admin_panel_kb())
        context.user_data['wait']=None; return
    if wait=="set_perc":
        try: perc=float(txt.replace('%','')); cfg=get_cfg(); cfg['perc']=perc; save_file("config.json", cfg); await update.message.reply_text(f"✅ Perc set {perc}%", reply_markup=admin_panel_kb())
        except: await update.message.reply_text("Send number e.g. 65")
        context.user_data['wait']=None; return
    if "USD" in txt or "$" in txt:
        # direct add if admin typed card without clicking Add Stock
        if uid==ADMIN_ID:
            m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
            if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
            if m:
                amt=float(m.group(1)); context.user_data['pending']=txt; context.user_data['amt']=amt; context.user_data['wait']="set_price"
                cfg=get_cfg(); calc=round(amt*cfg['perc']/100,2)
                await update.message.reply_text(f"Detected avl $ {amt} -> ${calc}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Use {cfg['perc']}%", callback_data="use_perc")]])); return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id
    if d=="main_menu": await q.edit_message_text(welcome_text(), reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="top_admin": await q.edit_message_text(admin_panel_text(), reply_markup=admin_panel_kb()); return
    if d=="top_list": prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]; msg=premium(f"LISTINGS {len(active)}")+"\n"; kb=[];
    for pid,p in active[-10:][::-1]: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}\n"; kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("🏠 Main", callback_data="main_menu")]); await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="top_bal": u=get_user(uid)[str(uid)]; await q.edit_message_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}", reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_dep": await q.edit_message_text(premium("DEPOSIT")+"Choose:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return
    if d=="top_filter": await q.edit_message_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎁 Gift", callback_data="filter_gift"), InlineKeyboardButton("All", callback_data="filter_all")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return
    if d=="top_sup" or d=="top_refund": await q.edit_message_text(premium("SUPPORT & REFUND")+f"🆘 @toma\n↩️ Invalid=Refund 10m\nProof needed\n📢 {STOCK_CHANNEL_LINK}", reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="top_channel": await q.edit_message_text(premium("STOCK CHANNEL")+f"{STOCK_CHANNEL_LINK}", reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="dep_ltc":
        qr=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={LTC_ADDRESS}"
        await q.edit_message_text(premium("LTC DEPOSIT")+f"`{LTC_ADDRESS}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]]))
        try: await context.bot.send_photo(chat_id=q.message.chat_id, photo=qr, caption=f"LTC QR {LTC_ADDRESS}")
        except: pass
        return
    if d=="dep_sol":
        qr=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={SOL_ADDRESS}"
        await q.edit_message_text(premium("SOL DEPOSIT")+f"`{SOL_ADDRESS}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]]))
        try: await context.bot.send_photo(chat_id=q.message.chat_id, photo=qr, caption=f"SOL QR {SOL_ADDRESS}")
        except: pass
        return

    # ADMIN PANEL BUTTONS - EXACT AS SCREENSHOT
    if d=="add_stock": context.user_data['wait']="add_stock"; await q.edit_message_text("➕ Send card: 451R...USD$3.39\nAgent will make avl $ small", reply_markup=admin_panel_kb()); return
    if d=="set_perc": context.user_data['wait']="set_perc"; await q.edit_message_text("💲 Send new perc e.g. 65 or 39", reply_markup=admin_panel_kb()); return
    if d=="add_bal": context.user_data['wait']="add_bal"; await q.edit_message_text("💵 Add Balance\nFormat: USERID AMOUNT\nEx: 7634497248 50", reply_markup=admin_panel_kb()); return
    if d=="relist_admin":
        prods=load_file("products.json"); sold=[(k,v) for k,v in prods.items() if v.get('sold')]
        if not sold: await q.edit_message_text("No sold to relist", reply_markup=admin_panel_kb()); return
        msg=premium("RELIST")+"\n"; kb=[]
        for pid,p in sold[-10:]: msg+=f"💎 {p['code'][:4]}... ${p['price']}\n"; kb.append([InlineKeyboardButton(f"♻️ {p['code'][:4]}... Relist", callback_data=f"do_relist_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("do_relist_"):
        pid=d.replace("do_relist_",""); prods=load_file("products.json")
        if pid in prods: prods[pid]['sold']=False; save_file("products.json", prods); await q.edit_message_text(f"✅ Relisted {pid}", reply_markup=admin_panel_kb())
        return
    if d=="vendor_req":
        users=load_file("users.json"); req=[k for k,v in users.items() if v.get('requests_vendor')]
        msg=premium("VENDOR REQ")+f"\n{len(req)} requests\n"; kb=[]
        for uid_r in req[-10:]: kb.append([InlineKeyboardButton(f"✅ Approve {uid_r}", callback_data=f"app_vendor_{uid_r}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else admin_panel_kb()); return
    if d.startswith("app_vendor_"):
        uid_r=d.replace("app_vendor_",""); users=load_file("users.json")
        if uid_r in users: users[uid_r]['is_vendor']=True; users[uid_r]['requests_vendor']=False; save_file("users.json", users); await q.edit_message_text(f"✅ Vendor approved {uid_r}", reply_markup=admin_panel_kb())
        return
    if d=="all_sellers":
        users=load_file("users.json"); sellers=[(k,v) for k,v in users.items() if v.get('is_vendor')]
        msg=premium(f"ALL SELLERS {len(sellers)}")+"\n"
        for k,v in sellers[-15:]: msg+=f"👤 {k} Bal:${v.get('balance',0)} Sales:${v.get('vendor_sales',0)}\n"
        await q.edit_message_text(msg, reply_markup=admin_panel_kb()); return
    if d=="orders":
        orders=load_file("orders.json"); pend=[(k,v) for k,v in orders.items() if v.get('status')=='pending']
        msg=premium(f"PENDING ORDERS {len(pend)}")+"\n"; kb=[]
        for oid,o in pend[-10:]: msg+=f"⏳ {oid} Buyer:{o['buyer_id']} ${o['price']}\n"; kb.append([InlineKeyboardButton(f"✅ {oid} Approve", callback_data=f"approve_{oid}"), InlineKeyboardButton(f"❌ Reject", callback_data=f"reject_{oid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else admin_panel_kb()); return
    if d=="sales_hist":
        orders=load_file("orders.json"); done=[(k,v) for k,v in orders.items() if v.get('status')=='completed']
        msg=premium(f"SALES HISTORY {len(done)}")+"\n"
        total=sum([v['price'] for k,v in done])
        msg+=f"Total Sales: ${total}\n"
        for oid,o in done[-10:]: msg+=f"✅ {oid} ${o['price']} Buyer:{o['buyer_id']}\n"
        await q.edit_message_text(msg, reply_markup=admin_panel_kb()); return
    if d=="buyer_hist":
        users=load_file("users.json"); msg=premium("BUYER HISTORY")+"\n"
        for uid_k,u in list(users.items())[-10:]: msg+=f"👤 {uid_k} Purchases:{len(u.get('purchases',[]))} Bal:${u.get('balance',0)}\n"
        await q.edit_message_text(msg, reply_markup=admin_panel_kb()); return
    if d.startswith("approve_"):
        oid=d.replace("approve_",""); orders=load_file("orders.json"); o=orders.get(oid)
        if o: o['status']="completed"; save_file("orders.json", orders); prods=load_file("products.json"); [prods.__setitem__(pid, {**pr, 'sold':True}) for pid,pr in prods.items() if pr['code']==o['code']]; save_file("products.json", prods)
        await q.edit_message_text(f"✅ {oid} Approved", reply_markup=admin_panel_kb()); return
    if d.startswith("reject_"):
        oid=d.replace("reject_",""); orders=load_file("orders.json"); o=orders.get(oid)
        if o: o['status']="rejected"; save_file("orders.json", orders); users=load_file("users.json"); b=str(o['buyer_id']); users[b]['balance']=users[b].get('balance',0)+o['price']; save_file("users.json", users)
        await q.edit_message_text(f"❌ {oid} Rejected & refunded", reply_markup=admin_panel_kb()); return
    if d=="use_perc":
        cfg=get_cfg(); amt=context.user_data.get('amt',3.39); calc=round(amt*cfg['perc']/100,2)
        pid=str(uuid.uuid4())[:6]; prods=load_file("products.json")
        prods[pid]={"code":context.user_data['pending'], "avl":f"avl $ {amt}", "price":calc, "sold":False, "owner":uid}
        save_file("products.json", prods); context.user_data['wait']=None
        await q.edit_message_text(f"✅ Added {pid} @ ${calc} (Perc {cfg['perc']}%)", reply_markup=admin_panel_kb())
        await auto_post(context, [prods[pid]]); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); p=load_file("products.json").get(pid)
        if not p: return
        await q.edit_message_text(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy ${p['price']}", callback_data=f"buy_{pid}")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return

async def run_bot():
    print("BOT INIT v34 ADMIN RESTORED")
    app=Application.builder().token(BOT_TOKEN).post_init(set_cmds).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("listings", listings_h))
    app.add_handler(CommandHandler("balance", balance_h))
    app.add_handler(CommandHandler("deposit", deposit_h))
    app.add_handler(CommandHandler("filter", filter_h))
    app.add_handler(CallbackQueryHandler(cb_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    await app.initialize(); await app.start()
    await app.updater.start_polling()
    print("✅ POLLING LIVE v34")
    while True: await asyncio.sleep(3600)

def run_thread(): asyncio.run(run_bot())
if __name__ == "__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
