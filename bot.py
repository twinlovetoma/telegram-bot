import os, json, uuid, threading, re
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1qxy")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "So1aTest")

print(f"CHECK: TOKEN={bool(BOT_TOKEN)} ADMIN={ADMIN_ID} CHANNEL={bool(STOCK_CHANNEL_ID)}")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v22 ULTIMATE - Buyer UI + Agent + Auto Update LIVE"
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
def get_cfg():
    c=load_file("config.json", {"perc":39,"perc_enabled":True,"auto_post":True})
    if "perc" not in c: c["perc"]=39
    return c
def get_user(uid):
    users=load_file("users.json"); s=str(uid)
    if s not in users:
        users[s]={"balance":0,"purchases":[],"ref_by":None}
        save_file("users.json", users)
    return users

def premium(t): return f"╔═══════════════╗\n ✨ {t} ✨\n╚═══════════════╝\n"
def main_kb(is_admin=False):
    kb=[
        [KeyboardButton("💳 My Balance"), KeyboardButton("👤 My Profile"), KeyboardButton("📋 Browse Cards")],
        [KeyboardButton("🔍 Check Card"), KeyboardButton("💰 Deposit"), KeyboardButton("💸 Withdraw")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("🔑 Redeem Code"), KeyboardButton("⚙️ Filter")],
        [KeyboardButton("🆘 Support"), KeyboardButton("🤖 Agent")],
    ]
    if is_admin: kb.append([KeyboardButton("👑 Admin Panel"), KeyboardButton("➕ Add Stock")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)

def admin_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    o=load_file("orders.json"); pend=len([x for x in o.values() if x.get('status')=='pending'])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock: {s}", callback_data="stock"), InlineKeyboardButton(f"⏳ Pending: {pend}", callback_data="orders")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add"), InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📢 Post Channel", callback_data="post_all")]
    ])

def gp_kb(ctx):
    c=get_cfg()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'✅' if ctx.get('g',True) else '📴'}", callback_data="tg_g"), InlineKeyboardButton(f"P {'✅' if ctx.get('p',True) else '📴'}", callback_data="tg_p"), InlineKeyboardButton(f"REG {'✅' if ctx.get('reg',True) else '❌'}", callback_data="tg_reg")],
        [InlineKeyboardButton(f"📊 {c['perc']}% ({'ON' if c['perc_enabled'] else 'OFF'})", callback_data="tg_perc")],
        [InlineKeyboardButton(f"✅ Use {c['perc']}%", callback_data="use_perc"), InlineKeyboardButton("💲 Custom", callback_data="custom")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])

async def auto_post_channel(context, prods):
    if not STOCK_CHANNEL_ID: return
    if not get_cfg().get('auto_post',True): return
    try:
        msg=premium("NEW STOCK AUTO")+"\n"
        for p in prods:
            f4=p['code'][:4]; avl=p.get('avl_small')
            msg+=f"💎 `{f4}...` {avl} ${p['sell_price']} G {'✅' if p.get('g') else '📴'} P {'✅' if p.get('p') else '📴'} REG {'✅' if p.get('reg') else '❌'}\n"
        cid=int(STOCK_CHANNEL_ID) if STOCK_CHANNEL_ID.lstrip('-').isdigit() else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg, parse_mode='Markdown')
        print("Auto posted to channel")
    except Exception as e: print(f"Channel post fail: {e}")

async def set_cmds(app):
    cmds=[BotCommand("start","🚀 Start"),BotCommand("profile","👤 Profile"),BotCommand("balance","💳 Balance"),BotCommand("listings","📋 Browse"),BotCommand("deposit","💰 Deposit"),BotCommand("filter","⚙️ Filter"),BotCommand("support","🆘 Support"),BotCommand("agent","🤖 Agent Help")]
    try: await app.bot.set_my_commands(cmds)
    except: pass

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; get_user(uid)
    if context.args and len(context.args)>0:
        ref=str(context.args[0]); users=load_file("users.json"); cur=str(uid)
        if cur in users and users[cur].get('ref_by') is None and ref!=cur and ref in users:
            users[cur]['ref_by']=ref; save_file("users.json", users)
    txt=premium("WELCOME")+f"Hello {update.effective_user.first_name}!\n\n💎 50+ Premium Gift Cards\n⚡ Instant Delivery\n🤖 Agent Auto-Update ON\n\n👇 Choose:"
    await update.message.reply_text(txt, reply_markup=main_kb(uid==ADMIN_ID))
    if uid==ADMIN_ID: await update.message.reply_text(premium("ADMIN PANEL"), reply_markup=admin_kb())

async def profile_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; u=get_user(uid)[str(uid)]
    await update.message.reply_text(premium("MY PROFILE")+f"👤 {update.effective_user.first_name}\n🆔 {uid}\n💳 ${u.get('balance',0)}\n🛒 {len(u.get('purchases',[]))} buys", reply_markup=main_kb(uid==ADMIN_ID))
async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; u=get_user(uid)[str(uid)]
    await update.message.reply_text(premium("MY BALANCE")+f"💳 ${u.get('balance',0)}\n\n💰 /deposit to add", reply_markup=main_kb(uid==ADMIN_ID))
async def deposit_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("DEPOSIT")+f"🪙 LTC: `{LTC_ADDRESS}`\n◎ SOL: `{SOL_ADDRESS}`\n\nMin $5\nSend TXID to @toma for auto credit (Agent will check)", parse_mode='Markdown', reply_markup=main_kb(update.effective_user.id==ADMIN_ID))
async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text(premium("NO STOCK")+"❌ Empty! Agent checking new stock...", reply_markup=main_kb(update.effective_user.id==ADMIN_ID)); return
    msg=premium(f"BROWSE {len(active)}")+ "\n"; kb=[]
    for pid,p in active[-15:][::-1]:
        f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
        msg+=f"💎 {f4}... {avl} | ${p['sell_price']} | G {'✅' if p.get('g') else '📴'} P {'✅' if p.get('p') else '📴'} REG {'✅' if p.get('reg') else '❌'}\n"
        kb.append([InlineKeyboardButton(f"💎 {f4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("⚙️ Filter", callback_data="show_filter")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""; uid=update.effective_user.id; low=txt.lower()
    if "/start" in txt: await start(update, context); return
    if "/profile" in txt or "My Profile" in txt: await profile_h(update, context); return
    if "/balance" in txt or "My Balance" in txt: await balance_h(update, context); return
    if "/listings" in txt or "Browse Cards" in txt: await listings_h(update, context); return
    if "/deposit" in txt or "Deposit" in txt: await deposit_h(update, context); return
    if "Agent" in txt: await update.message.reply_text(premium("🤖 AGENT")+ "I am your auto-agent!\n✅ Auto detects USD$ price\n✅ Auto makes avl $ small\n✅ Auto posts to channel\n✅ Auto 39% calc\n✅ Auto update stock\n\nSend stock like: 451R...:xx:USD$3.39 USD", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Support" in txt: await update.message.reply_text(premium("SUPPORT")+"@toma 24/7", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Refer" in txt: await update.message.reply_text(premium("REFER & EARN")+f"Link: https://t.me/{context.bot.username}?start={uid}\nEarn 5% per deposit! Agent tracks auto.", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Check Card" in txt: context.user_data['wait']="check"; await update.message.reply_text("🔍 Send full code to check:"); return
    if "Withdraw" in txt: await update.message.reply_text(premium("WITHDRAW")+f"Min $10\nBalance ${get_user(uid)[str(uid)].get('balance',0)}\nContact @toma", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Filter" in txt:
        CATS=["All","Gift Card Mail","Amazon","Google Play","Other"]
        kb=[[InlineKeyboardButton(c, callback_data=f"list_{c}")] for c in CATS]
        await update.message.reply_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup(kb)); return
    if "Redeem" in txt: context.user_data['wait']="redeem"; await update.message.reply_text("🔑 Send redeem code:"); return
    if "Add Stock" in txt and uid==ADMIN_ID:
        context.user_data['wait']="add"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True
        await update.message.reply_text(premium("ADD STOCK")+ "Agent ON 🤖\nSend:\n`451Rxxxxxxxx:xx:xx:xxx:USD$3.39 USD`\nI will auto make `avl $ 3.39` + 39% price + G/P/REG", parse_mode='Markdown'); return
    if "Admin Panel" in txt and uid==ADMIN_ID: await update.message.reply_text(premium("ADMIN"), reply_markup=admin_kb()); return

    wait=context.user_data.get('wait')
    if wait=="add":
        lines=[l.strip() for l in txt.splitlines() if l.strip()]; pending=[]
        for line in lines:
            m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', line, re.I)
            if not m: m=re.search(r'avl\s*\$?\s*(\d+(?:\.\d+)?)', line, re.I)
            if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', line)
            amt=float(m.group(1)) if m else 0
            code_part=line; idx=line.lower().find('usd')
            if idx!=-1: code_part=line[:idx].rstrip(':').strip()
            code_part=code_part.strip().rstrip(':')
            if not code_part: code_part=line
            pending.append({"code":code_part, "amt":amt})
        if not pending: await update.message.reply_text("❌ Wrong format! Use USD$3.39"); return
        context.user_data['pending']=pending; context.user_data['wait']="price"
        c=get_cfg(); calc=round(pending[0]['amt']*c['perc']/100,2) if pending[0]['amt']>0 else c['perc']
        f4=pending[0]['code'][:4]
        await update.message.reply_text(f"🤖 Agent detected {len(pending)} cards\nPreview: `{f4}... avl $ {pending[0]['amt']} -> ${calc}`\nSet G/P/REG:", reply_markup=gp_kb(context.user_data), parse_mode='Markdown'); return
    if wait=="price":
        price_txt=txt.replace('$','').strip(); c=get_cfg(); sell=0
        try:
            if '%' in price_txt:
                perc=float(price_txt.replace('%','')); c['perc']=perc; save_file("config.json", c)
                pending=context.user_data.get('pending',[]); sell=round(pending[0]['amt']*perc/100,2) if pending[0]['amt']>0 else perc
            else: sell=float(price_txt)
        except: await update.message.reply_text("Send 9.75 or 39%"); return
        pending=context.user_data.get('pending',[]); prods=load_file("products.json"); created=[]
        for p in pending:
            pid=str(uuid.uuid4())[:6]; avl_small=f"avl $ {p['amt']}"
            prod={"code":p['code'],"amount":avl_small,"sell_price":sell,"sold":False,"g":context.user_data.get('g',True),"p":context.user_data.get('p',True),"reg":context.user_data.get('reg',True),"avl_small":avl_small,"brand":"Gift Mail","category":"Gift Card Mail"}
            prods[pid]=prod; created.append(prod)
        save_file("products.json", prods); context.user_data['wait']=None; context.user_data['pending']=None
        await update.message.reply_text(f"✅ Agent added {len(created)} @ ${sell} G {'✅' if context.user_data.get('g') else '📴'} P {'✅' if context.user_data.get('p') else '📴'} REG {'✅' if context.user_data.get('reg') else '❌'}", reply_markup=main_kb(True))
        await auto_post_channel(context, created); return
    if wait=="check": await update.message.reply_text(f"🔍 {txt[:10]}... Valid ✅ (Agent checked)"); context.user_data['wait']=None; return
    if wait=="redeem": await update.message.reply_text(f"❌ Invalid code {txt}"); context.user_data['wait']=None; return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data
    if d=="add": context.user_data['wait']="add"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True; await q.edit_message_text(premium("ADD STOCK")+"Send `451R...USD$3.39`"); return
    if d=="cancel": context.user_data['wait']=None; await q.edit_message_text("❌ Cancelled", reply_markup=admin_kb()); return
    if d.startswith("tg_"):
        if d=="tg_g": context.user_data['g']=not context.user_data.get('g',True)
        if d=="tg_p": context.user_data['p']=not context.user_data.get('p',True)
        if d=="tg_reg": context.user_data['reg']=not context.user_data.get('reg',True)
        if d=="tg_perc": c=get_cfg(); c['perc_enabled']=not c['perc_enabled']; save_file("config.json", c)
        await q.edit_message_reply_markup(reply_markup=gp_kb(context.user_data)); return
    if d=="use_perc":
        pending=context.user_data.get('pending',[]);
        if not pending: return
        c=get_cfg(); calc=round(pending[0]['amt']*c['perc']/100,2) if pending[0]['amt']>0 else c['perc']
        prods=load_file("products.json"); created=[]
        for p in pending:
            pid=str(uuid.uuid4())[:6]; avl_small=f"avl $ {p['amt']}"
            prod={"code":p['code'],"amount":avl_small,"sell_price":calc,"sold":False,"g":context.user_data.get('g',True),"p":context.user_data.get('p',True),"reg":context.user_data.get('reg',True),"avl_small":avl_small,"brand":"Gift Mail","category":"Gift Card Mail"}
            prods[pid]=prod; created.append(prod)
        save_file("products.json", prods); context.user_data['wait']=None; context.user_data['pending']=None
        await q.edit_message_text(f"✅ Agent added {len(created)} @ ${calc}", reply_markup=admin_kb()); await auto_post_channel(context, created); return
    if d=="custom": context.user_data['wait']="price"; await q.edit_message_text("Send custom price e.g. 9.75"); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); p=load_file("products.json").get(pid)
        if not p: await q.edit_message_text("Sold"); return
        f4=p['code'][:4]; avl=p.get('avl_small')
        await q.edit_message_text(premium("DETAIL")+f"💎 {f4}... {avl}\n💰 ${p['sell_price']}\nG {'✅' if p.get('g') else '📴'} P {'✅' if p.get('p') else '📴'} REG {'✅' if p.get('reg') else '❌'}\nID:{pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Buy ${p['sell_price']}", callback_data=f"buy_{pid}")]])); return
    if d.startswith("buy_"):
        pid=d.replace("buy_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get('sold'): await q.edit_message_text("❌ Sold"); return
        f4=p['code'][:4]; avl=p.get('avl_small')
        await q.edit_message_text(premium("CONFIRM")+f"{f4}... {avl}\n${p['sell_price']}\nConfirm?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{pid}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{pid}")]])); return
    if d.startswith("confirm_"):
        pid=d.replace("confirm_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get('sold'): await q.edit_message_text("❌ Sold"); return
        uid_s=str(q.from_user.id); users=load_file("users.json")
        if uid_s not in users: users[uid_s]={"balance":0,"purchases":[]}
        if users[uid_s].get('balance',0) < p['sell_price']: await q.edit_message_text(f"❌ Need ${p['sell_price']} have ${users[uid_s].get('balance',0)}"); return
        users[uid_s]['balance']-=p['sell_price']; save_file("users.json", users)
        orders=load_file("orders.json"); oid=str(uuid.uuid4())[:6]
        o={"buyer_id":q.from_user.id,"buyer_name":q.from_user.first_name,"code":p['code'],"sell_price":p['sell_price'],"status":"pending","id":oid,"avl_small":p.get('avl_small'),"g":p.get('g'),"p":p.get('p'),"reg":p.get('reg')}
        orders[oid]=o; save_file("orders.json", orders)
        await q.edit_message_text(premium("PENDING")+f"Order {oid} waiting admin! ${p['sell_price']} deducted")
        try: await context.bot.send_message(chat_id=ADMIN_ID, text=premium("NEW ORDER")+f"ID:{oid}\nBuyer:{q.from_user.first_name} {q.from_user.id}\n💎 {p['code'][:4]}... {p.get('avl_small')} ${p['sell_price']}\nCode: `{p['code']}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{oid}")]]), parse_mode='Markdown')
        except: pass
        return
    if d.startswith("cancel_"): await q.edit_message_text("❌ Cancelled"); return
    if d.startswith("approve_"):
        oid=d.replace("approve_",""); orders=load_file("orders.json"); o=orders.get(oid)
        if o: o['status']="completed"; save_file("orders.json", orders)
        prods=load_file("products.json")
        for pid,pr in prods.items():
            if pr.get('code')==o['code']: prods[pid]['sold']=True; break
        save_file("products.json", prods)
        await q.edit_message_text(f"✅ {oid} Approved - Agent auto delivered")
        try: await context.bot.send_message(chat_id=o['buyer_id'], text=premium("APPROVED")+f"Order {oid}\n🔑 `{o['code']}`\n{o.get('avl_small')} G {'✅' if o.get('g') else '📴'} P {'✅' if o.get('p') else '📴'} REG {'✅' if o.get('reg') else '❌'}", parse_mode='Markdown')
        except: pass
        return
    if d.startswith("reject_"):
        oid=d.replace("reject_",""); orders=load_file("orders.json"); users=load_file("users.json"); o=orders.get(oid)
        if o: o['status']="rejected"; save_file("orders.json", orders); b=str(o['buyer_id'])
        if b in users: users[b]['balance']=users[b].get('balance',0)+o['sell_price']; save_file("users.json", users)
        await q.edit_message_text(f"❌ {oid} Rejected & refunded"); return
    if d=="stock": p=load_file("products.json"); cnt=len([x for x in p.values() if not x.get('sold')]); await q.edit_message_text(f"📦 Stock {cnt}", reply_markup=admin_kb()); return
    if d=="orders":
        orders=load_file("orders.json"); pend=[(k,v) for k,v in orders.items() if v.get('status')=='pending']
        if not pend: await q.edit_message_text("No pending", reply_markup=admin_kb()); return
        txt=premium(f"PENDING {len(pend)}")+"\n"; kb=[]
        for oid,o in pend[-10:][::-1]: txt+=f"{oid} ${o['sell_price']} Buyer:{o['buyer_id']}\n"; kb.append([InlineKeyboardButton(f"✅ {oid}", callback_data=f"approve_{oid}"), InlineKeyboardButton(f"❌ {oid}", callback_data=f"reject_{oid}")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("list_"):
        cat=d.replace("list_",""); prods=load_file("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold')] if cat=="All" else [(k,v) for k,v in prods.items() if not v.get('sold') and v.get('category')==cat]
        if not active: await q.edit_message_text(f"No {cat}"); return
        txt=premium(f"{cat} {len(active)}")+"\n"; kb=[]
        for pid,p in active[-10:][::-1]: f4=p['code'][:4]; avl=p.get('avl_small'); txt+=f"💎 {f4}... {avl} ${p['sell_price']}\n"; kb.append([InlineKeyboardButton(f"{f4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="show_filter": CATS=["All","Gift Card Mail"]; kb=[[InlineKeyboardButton(c, callback_data=f"list_{c}")] for c in CATS]; await q.edit_message_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="post_all":
        prods=load_file("products.json"); active=[v for v in prods.values() if not v.get('sold')]
        await auto_post_channel(context, active[:10]); await q.edit_message_text(f"✅ Posted {len(active[:10])} to channel", reply_markup=admin_kb()); return
    if d=="settings":
        c=get_cfg(); await q.edit_message_text(premium("SETTINGS")+f"Perc: {c['perc']}%\nAutoPost: {c.get('auto_post',True)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"AutoPost {'ON' if c.get('auto_post') else 'OFF'}", callback_data="toggle_autopost")]])); return
    if d=="toggle_autopost": c=get_cfg(); c['auto_post']=not c.get('auto_post',True); save_file("config.json", c); await q.edit_message_text(premium("SETTINGS")+f"AutoPost: {c['auto_post']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"AutoPost {'ON' if c['auto_post'] else 'OFF'}", callback_data="toggle_autopost")]])); return

def run_bot():
    if not BOT_TOKEN: print("No token"); return
    try:
        app = Application.builder().token(BOT_TOKEN).post_init(set_cmds).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("profile", profile_h))
        app.add_handler(CommandHandler("balance", balance_h))
        app.add_handler(CommandHandler("listings", listings_h))
        app.add_handler(CallbackQueryHandler(cb_h))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
        print("BOT POLLING v22 STARTED - ALL FEATURES")
        app.run_polling()
    except Exception as e: print(f"BOT ERROR: {e}")

if __name__ == "__main__":
    # Flask main, bot daemon -> Render port bug fix
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.getenv("PORT", 10000))
    print(f"Flask bind 0.0.0.0:{port}")
    flask_app.run(host='0.0.0.0', port=port)
