import os, json, uuid, threading, re, time
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6699688350"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1qtest")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "soltest")

print(f"ENV CHECK: BOT_TOKEN={bool(BOT_TOKEN)} ADMIN={ADMIN_ID}")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "18.0 PREMIUM UI LIVE"
@flask_app.route('/health')
def health(): return "OK"
def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
threading.Thread(target=run_flask, daemon=True).start()

def load_file(f,d=None):
    if d is None: d={}
    if not os.path.exists(f): return d
    try:
        with open(f,'r') as x: return json.load(x)
    except: return d
def save_file(f,d):
    with open(f,'w') as x: json.dump(d, x, indent=2)
def get_cfg():
    defa={"perc":39,"perc_enabled":True}
    c=load_file("config.json", defa)
    for k,v in defa.items():
        if k not in c: c[k]=v
    return c
def get_user(uid_s):
    users=load_file("users.json")
    if uid_s not in users:
        users[uid_s]={"balance":0,"purchases":[]}
        save_file("users.json", users)
    return users

def premium_header(t): return f"╔═══════════════╗\n ✨ {t} ✨\n╚═══════════════╝\n"
def main_kb(is_admin=False):
    kb=[
        [KeyboardButton("💳 My Balance"), KeyboardButton("👤 My Profile"), KeyboardButton("📋 Browse Cards")],
        [KeyboardButton("🔍 Check Card"), KeyboardButton("💰 Deposit"), KeyboardButton("💸 Withdraw")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("🔑 Redeem Code"), KeyboardButton("⚙️ Filter")],
        [KeyboardButton("🆘 Support")],
    ]
    if is_admin:
        kb.append([KeyboardButton("👑 Admin Panel"), KeyboardButton("➕ Add Stock")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)

def admin_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Stock: {s}", callback_data="stock")],[InlineKeyboardButton("➕ Add Stock", callback_data="add")],[InlineKeyboardButton("⏳ Pending", callback_data="orders")]])

def build_gp_kb(ctx):
    c=get_cfg(); g=ctx.get('g',True); pp=ctx.get('p',True); reg=ctx.get('reg',True)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'✅' if g else '📴'}", callback_data="toggle_g"), InlineKeyboardButton(f"P {'✅' if pp else '📴'}", callback_data="toggle_p"), InlineKeyboardButton(f"REGISTERED {'✅' if reg else '❌'}", callback_data="toggle_reg")],
        [InlineKeyboardButton(f"📊 {c['perc']}% ({'ON ✅' if c['perc_enabled'] else 'OFF ❌'})", callback_data="toggle_perc")],
        [InlineKeyboardButton(f"✅ Use {c['perc']}% Price", callback_data="use_perc"), InlineKeyboardButton("💲 Custom $9.75", callback_data="custom_price")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")],
    ])

async def post_channel(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium_header("NEW STOCK")+"\n"
        for p in prods:
            f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
            msg+=f"💎 `{f4}...` {avl} | ${p['sell_price']} | G {'✅' if p.get('g') else '📴'} P {'✅' if p.get('p') else '📴'} REG {'✅' if p.get('reg') else '❌'}\n"
        cid=int(STOCK_CHANNEL_ID) if not STOCK_CHANNEL_ID.startswith('@') else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg, parse_mode='Markdown')
    except Exception as e: print(e)

async def set_cmds(app):
    cmds=[BotCommand("start","🚀 Start"),BotCommand("profile","👤 Profile"),BotCommand("balance","💳 Balance"),BotCommand("listings","📋 Browse"),BotCommand("deposit","💰 Deposit"),BotCommand("filter","⚙️ Filter"),BotCommand("support","🆘 Support")]
    try: await app.bot.set_my_commands(cmds)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; get_user(str(uid))
    txt=premium_header("WELCOME")+f"Hello {update.effective_user.first_name}!\n\n50+ Gift Cards · Instant Delivery ⚡\n💎 Premium Store\n💰 Trusted & Fast\n\n👇 Choose from below:"
    await update.message.reply_text(txt, reply_markup=main_kb(uid==ADMIN_ID))
    if uid==ADMIN_ID:
        await update.message.reply_text(premium_header("ADMIN PANEL"), reply_markup=admin_kb())

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; u=get_user(str(uid))[str(uid)]
    await update.message.reply_text(premium_header("MY PROFILE")+f"👤 {update.effective_user.first_name}\n🆔 {uid}\n💳 Balance: ${u.get('balance',0)}\n🛒 Purchases: {len(u.get('purchases',[]))}", reply_markup=main_kb(uid==ADMIN_ID))
async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; u=get_user(str(uid))[str(uid)]
    await update.message.reply_text(premium_header("MY BALANCE")+f"💳 Balance: ${u.get('balance',0)}\n\nDeposit via /deposit", reply_markup=main_kb(uid==ADMIN_ID))
async def deposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium_header("DEPOSIT")+f"🪙 LTC: `{LTC_ADDRESS}`\n◎ SOL: `{SOL_ADDRESS}`\nMin $5 - Send proof to @toma", parse_mode='Markdown', reply_markup=main_kb(update.effective_user.id==ADMIN_ID))
async def listings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active:
        await update.message.reply_text(premium_header("NO STOCK")+"❌ No cards now!", reply_markup=main_kb(update.effective_user.id==ADMIN_ID)); return
    msg=premium_header(f"BROWSE {len(active)} CARDS")+"\n"; kb=[]
    for pid,p in active[-15:][::-1]:
        f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
        msg+=f"💎 {f4}... {avl} ${p['sell_price']} G {'✅' if p.get('g') else '📴'} P {'✅' if p.get('p') else '📴'} REG {'✅' if p.get('reg') else '❌'}\n"
        kb.append([InlineKeyboardButton(f"💎 {f4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("⚙️ Filter", callback_data="show_filter")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    CATS=["All","Gift Card Mail","Free Fire","Call of Duty","Amazon","Google Play","Other"]
    kb=[[InlineKeyboardButton(c, callback_data=f"listings_{c}")] for c in CATS]
    await update.message.reply_text(premium_header("FILTER"), reply_markup=InlineKeyboardMarkup(kb))
async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium_header("SUPPORT")+"🆘 @toma - 24/7", reply_markup=main_kb(update.effective_user.id==ADMIN_ID))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip(); uid=update.effective_user.id; low=txt.lower()
    if txt.startswith('/start'): await start(update, context); return
    if txt.startswith('/profile'): await profile_cmd(update, context); return
    if txt.startswith('/balance'): await balance_cmd(update, context); return
    if txt.startswith('/deposit'): await deposit_cmd(update, context); return
    if txt.startswith('/listings'): await listings_cmd(update, context); return
    if txt.startswith('/filter'): await filter_cmd(update, context); return
    if txt.startswith('/support'): await support_cmd(update, context); return

    if "My Balance" in txt or "my balance" in low: await balance_cmd(update, context); return
    if "My Profile" in txt or "my profile" in low: await profile_cmd(update, context); return
    if "Browse Cards" in txt: await listings_cmd(update, context); return
    if "Deposit" in txt: await deposit_cmd(update, context); return
    if "Withdraw" in txt: await update.message.reply_text(premium_header("WITHDRAW")+f"Min $10 - Contact @toma\nBalance ${get_user(str(uid))[str(uid)].get('balance',0)}", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Filter" in txt: await filter_cmd(update, context); return
    if "Support" in txt: await support_cmd(update, context); return
    if "Refer" in txt: await update.message.reply_text(premium_header("REFER & EARN")+f"Link: https://t.me/{context.bot.username}?start={uid}\nEarn 5%!", reply_markup=main_kb(uid==ADMIN_ID)); return
    if "Redeem" in txt: context.user_data['wait']="redeem"; await update.message.reply_text("🔑 Send code:"); return
    if "Check Card" in txt: context.user_data['wait']="check"; await update.message.reply_text("🔍 Send code to check:"); return
    if "Add Stock" in txt and uid==ADMIN_ID: context.user_data['wait']="add_codes"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True; await update.message.reply_text(premium_header("ADD STOCK")+"Send:\n`451Rxxxxxxxx:xx:xx:xxx:USD$3.39 USD`\nBot makes `avl $ 3.39`", parse_mode='Markdown'); return
    if "Admin Panel" in txt and uid==ADMIN_ID: await update.message.reply_text(premium_header("ADMIN PANEL"), reply_markup=admin_kb()); return

    wait=context.user_data.get('wait')
    if wait=="add_codes":
        lines=[l.strip() for l in txt.splitlines() if l.strip()]; pending=[]
        for line in lines:
            m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', line, re.I)
            if not m: m=re.search(r'avl\s*\$?\s*(\d+(?:\.\d+)?)', line, re.I)
            if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', line)
            amount=float(m.group(1)) if m else 0
            code_part=line; idx=line.lower().find('usd')
            if idx!=-1: code_part=line[:idx].rstrip(':').strip()
            code_part=code_part.strip().rstrip(':')
            if not code_part: code_part=line
            pending.append({"code":code_part, "amount_val":amount, "raw":line})
        if not pending: await update.message.reply_text("❌ Format: 451R...:xx:xx:xxx:USD$3.39 USD"); return
        context.user_data['pending']=pending; context.user_data['wait']="add_price"
        c=get_cfg(); calc=round(pending[0]['amount_val']*c['perc']/100,2) if pending[0]['amount_val']>0 else c['perc']
        f4=pending[0]['code'][:4]
        await update.message.reply_text(f"✅ {len(pending)} found\nPreview: `{f4}... avl $ {pending[0]['amount_val']} | Price ${calc}`\nSet G/P/REG:", reply_markup=build_gp_kb(context.user_data), parse_mode='Markdown'); return

    if wait=="add_price":
        price_txt=txt.replace('$','').strip(); c=get_cfg(); sell=0
        try:
            if '%' in price_txt:
                perc=float(price_txt.replace('%','')); c['perc']=perc; save_file("config.json", c)
                pending=context.user_data.get('pending',[]); sell=round(pending[0]['amount_val']*perc/100,2) if pending[0]['amount_val']>0 else perc
            else: sell=float(price_txt)
        except: await update.message.reply_text("Type 9.75 or 39%"); return
        pending=context.user_data.get('pending',[]); prods=load_file("products.json"); created=[]
        for p in pending:
            pid=str(uuid.uuid4())[:6]; avl_small=f"avl $ {p['amount_val']}"
            prod={"code":p['code'],"amount":avl_small,"sell_price":sell,"sold":False,"g":context.user_data.get('g',True),"p":context.user_data.get('p',True),"reg":context.user_data.get('reg',True),"avl_small":avl_small,"brand":"Gift Mail","category":"Gift Card Mail"}
            prods[pid]=prod; created.append(prod)
        save_file("products.json", prods); context.user_data['wait']=None; context.user_data['pending']=None
        await update.message.reply_text(f"✅ Added {len(created)} @ ${sell}", reply_markup=main_kb(True)); await post_channel(context, created); return
    if wait=="redeem": await update.message.reply_text(f"❌ Invalid {txt}", reply_markup=main_kb(uid==ADMIN_ID)); context.user_data['wait']=None; return
    if wait=="check": await update.message.reply_text(f"🔍 {txt[:8]}... Valid ✅ (demo)", reply_markup=main_kb(uid==ADMIN_ID)); context.user_data['wait']=None; return

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data
    if d=="add": context.user_data['wait']="add_codes"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True; await q.edit_message_text(premium_header("ADD STOCK")+"Send: `451R...:xx:xx:xxx:USD$3.39 USD`", parse_mode='Markdown'); return
    if d=="cancel_add": context.user_data['wait']=None; await q.edit_message_text("❌ Cancelled", reply_markup=admin_kb()); return
    if d=="toggle_g": context.user_data['g']=not context.user_data.get('g',True); await q.edit_message_reply_markup(reply_markup=build_gp_kb(context.user_data)); return
    if d=="toggle_p": context.user_data['p']=not context.user_data.get('p',True); await q.edit_message_reply_markup(reply_markup=build_gp_kb(context.user_data)); return
    if d=="toggle_reg": context.user_data['reg']=not context.user_data.get('reg',True); await q.edit_message_reply_markup(reply_markup=build_gp_kb(context.user_data)); return
    if d=="toggle_perc": c=get_cfg(); c['perc_enabled']=not c['perc_enabled']; save_file("config.json", c); await q.edit_message_reply_markup(reply_markup=build_gp_kb(context.user_data)); return
    if d=="use_perc":
        pending=context.user_data.get('pending',[]);
        if not pending: await q.edit_message_text("No pending"); return
        c=get_cfg(); calc=round(pending[0]['amount_val']*c['perc']/100,2) if pending[0]['amount_val']>0 else c['perc']
        prods=load_file("products.json"); created=[]
        for p in pending:
            pid=str(uuid.uuid4())[:6]; avl_small=f"avl $ {p['amount_val']}"
            prod={"code":p['code'],"amount":avl_small,"sell_price":calc,"sold":False,"g":context.user_data.get('g',True),"p":context.user_data.get('p',True),"reg":context.user_data.get('reg',True),"avl_small":avl_small,"brand":"Gift Mail","category":"Gift Card Mail"}
            prods[pid]=prod; created.append(prod)
        save_file("products.json", prods); context.user_data['wait']=None; context.user_data['pending']=None
        await q.edit_message_text(f"✅ Added {len(created)} @ ${calc}", reply_markup=admin_kb()); await post_channel(context, created); return
    if d=="custom_price": context.user_data['wait']="add_price"; await q.edit_message_text("Type custom price e.g. 9.75"); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p: await q.edit_message_text("Sold"); return
        f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
        await q.edit_message_text(premium_header("CARD DETAIL")+f"💎 {f4}... {avl}\n💰 ${p['sell_price']}\nG {'✅' if p.get('g') else '📴'} P {'✅' if p.get('p') else '📴'} REG {'✅' if p.get('reg') else '❌'}\n🆔 {pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Buy ${p['sell_price']}", callback_data=f"buy_{pid}")]])); return
    if d.startswith("buy_"):
        pid=d.replace("buy_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get('sold'): await q.edit_message_text("❌ Sold"); return
        f4=p['code'][:4]; avl=p.get('avl_small', p['amount'])
        await q.edit_message_text(premium_header("CONFIRM")+f"🎁 {f4}... {avl}\n💰 ${p['sell_price']}\nConfirm?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{pid}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{pid}")]])); return
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
        await q.edit_message_text(premium_header("PENDING")+f"Order {oid} waiting admin approval!\n${p['sell_price']} deducted")
        try: await context.bot.send_message(chat_id=ADMIN_ID, text=premium_header("NEW ORDER")+f"ID:{oid}\nBuyer:{q.from_user.first_name} {q.from_user.id}\n💎 {p['code'][:4]}... {p.get('avl_small')} ${p['sell_price']}\nCode: `{p['code']}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{oid}")]]), parse_mode='Markdown')
        except: pass
        return
    if d.startswith("cancel_"): await q.edit_message_text("❌ Cancelled", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Browse", callback_data="listings_All")]])); return
    if d.startswith("approve_"):
        oid=d.replace("approve_",""); orders=load_file("orders.json"); prods=load_file("products.json")
        o=orders.get(oid)
        if o:
            o['status']="completed"; save_file("orders.json", orders)
            for pid,pr in prods.items():
                if pr.get('code')==o['code']: prods[pid]['sold']=True; break
            save_file("products.json", prods)
            await q.edit_message_text(f"✅ {oid} Approved")
            try: await context.bot.send_message(chat_id=o['buyer_id'], text=premium_header("APPROVED")+f"Order {oid}\n🔑 `{o['code']}`\n{o.get('avl_small')} G {'✅' if o.get('g') else '📴'} P {'✅' if o.get('p') else '📴'} REG {'✅' if o.get('reg') else '❌'}", parse_mode='Markdown')
            except: pass
        return
    if d.startswith("reject_"):
        oid=d.replace("reject_",""); orders=load_file("orders.json"); users=load_file("users.json"); o=orders.get(oid)
        if o: o['status']="rejected"; save_file("orders.json", orders); b=str(o['buyer_id']);
        if b in users: users[b]['balance']=users[b].get('balance',0)+o['sell_price']; save_file("users.json", users)
        await q.edit_message_text(f"❌ {oid} Rejected & refunded"); return
    if d=="stock": p=load_file("products.json"); cnt=len([x for x in p.values() if not x.get('sold')]); await q.edit_message_text(f"Stock {cnt}", reply_markup=admin_kb()); return
    if d=="orders":
        orders=load_file("orders.json"); pend=[(k,v) for k,v in orders.items() if v.get('status')=='pending']
        if not pend: await q.edit_message_text("No pending", reply_markup=admin_kb()); return
        txt=premium_header(f"PENDING {len(pend)}")+"\n"; kb=[]
        for oid,o in pend[-10:][::-1]: txt+=f"{oid} ${o['sell_price']} Buyer:{o['buyer_id']}\n"; kb.append([InlineKeyboardButton(f"✅ {oid}", callback_data=f"approve_{oid}"), InlineKeyboardButton(f"❌ {oid}", callback_data=f"reject_{oid}")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("listings_"):
        cat=d.replace("listings_",""); prods=load_file("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold')] if cat=="All" else [(k,v) for k,v in prods.items() if not v.get('sold') and v.get('category')==cat]
        if not active: await q.edit_message_text(f"No {cat}"); return
        txt=premium_header(f"{cat} {len(active)}")+"\n"; kb=[]
 
