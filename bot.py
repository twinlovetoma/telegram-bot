import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
STOCK_CHANNEL_LINK = os.getenv("STOCK_CHANNEL_LINK", "https://t.me/prepaidsgift")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1q...")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "So1...")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v36 FINAL NO BUG - LIVE"
@flask_app.route('/health')
def health(): return "OK v36"

def load_file(f, default=None):
    try:
        if os.path.exists(f):
            with open(f,'r') as x: return json.load(x)
    except: pass
    return default if default is not None else {}

def save_file(f,d):
    with open(f,'w') as x: json.dump(d,x, indent=2)

def get_user(uid):
    users=load_file("users.json")
    s=str(uid)
    if s not in users:
        users[s]={"balance":0,"purchases":[],"is_vendor":False,"vendor_sales":0,"ref_by":None,"requests_vendor":False}
        save_file("users.json", users)
    return users

def get_cfg():
    c=load_file("config.json")
    return c if c else {"perc":39,"comm":5}

def premium(t): return f"╔══════╗ ✨ {t} ✨ ╚══════╝\n"

def top_menu(admin=False):
    kb=[
        [InlineKeyboardButton("📋 Listings", callback_data="top_list"), InlineKeyboardButton("💳 Balance", callback_data="top_bal"), InlineKeyboardButton("👤 Profile", callback_data="top_profile")],
        [InlineKeyboardButton("💰 Deposit", callback_data="top_dep"), InlineKeyboardButton("⚙️ Filter", callback_data="top_filter"), InlineKeyboardButton("🔍 Check", callback_data="top_check")],
        [InlineKeyboardButton("👥 Refer", callback_data="top_ref"), InlineKeyboardButton("🔑 Redeem", callback_data="top_redeem"), InlineKeyboardButton("🏪 Vendor", callback_data="top_vendor")],
        [InlineKeyboardButton("🆘 Support", callback_data="top_sup"), InlineKeyboardButton("↩️ Refund Rule", callback_data="top_refund"), InlineKeyboardButton("📢 Stock Channel", callback_data="top_channel")],
    ]
    if admin: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="top_admin")])
    return InlineKeyboardMarkup(kb)

def admin_panel_kb():
    cfg=get_cfg()
    prods=load_file("products.json")
    stock=len([x for x in prods.values() if not x.get('sold')])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock:{stock}", callback_data="stock_info"), InlineKeyboardButton(f"💲 Set {cfg['perc']}%", callback_data="set_perc")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add_stock"), InlineKeyboardButton("📢 Post Channel", callback_data="post_all")],
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
        f"Hello! 👋\n💎 50+ Cards | ⚡ Instant | 🤖 Agent ON | {cfg['perc']}%\n\n"
        "📋 /listings - Browse Cards\n"
        "💳 /balance - My Balance\n"
        "💰 /deposit - Deposit LTC/SOL\n"
        "⚙️ /filter - Filter Gift / All\n"
        "🔍 /check - Check Card\n"
        "👤 /profile - Profile + History + Relist\n"
        "🏪 /vendor - Vendor Dashboard\n"
        "👥 /refer - Refer & Earn\n"
        "🔑 /redeem - Redeem Code\n\n"
        "↩️ REFUND RULE:\n"
        "• Invalid card = Full refund / Replace in 10 min\n"
        "• Valid but used = No refund\n"
        "• Proof needed: screenshot/video\n\n"
        f"📢 Stock Channel: {STOCK_CHANNEL_LINK}\n"
        "🆘 /support - @toma 24/7\n\n"
        "👇 Choose from TOP - No bottom keyboard:"
    )

async def set_cmds(app):
    cmds=[
        BotCommand("start","🏠 Welcome + Rules + Stock"),
        BotCommand("listings","📋 Browse Cards"),
        BotCommand("balance","💳 My Balance"),
        BotCommand("deposit","💰 Deposit LTC/SOL"),
        BotCommand("filter","⚙️ Filter"),
        BotCommand("check","🔍 Check Card"),
        BotCommand("profile","👤 Profile + History"),
        BotCommand("vendor","🏪 Vendor Dashboard"),
        BotCommand("refer","👥 Refer & Earn"),
        BotCommand("redeem","🔑 Redeem Code"),
        BotCommand("support","🆘 Support & Refund Rule"),
        BotCommand("admin","👑 Admin Panel"),
    ]
    try:
        await app.bot.set_my_commands(cmds)
        print("Commands set")
    except Exception as e:
        print(f"Cmd error {e}")

async def auto_post(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium("NEW STOCK")+"\n"
        for p in prods: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅\n"
        cid=int(STOCK_CHANNEL_ID) if STOCK_CHANNEL_ID.lstrip('-').isdigit() else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg)
    except Exception as e:
        print(f"auto_post err {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    if context.args:
        ref=str(context.args[0])
        all_u=load_file("users.json")
        s=str(update.effective_user.id)
        if s in all_u and all_u[s].get('ref_by') is None and ref!=s and ref in all_u:
            all_u[s]['ref_by']=ref
            save_file("users.json", all_u)
    await update.message.reply_text(welcome_text(), reply_markup=top_menu(update.effective_user.id==ADMIN_ID), disable_web_page_preview=True)

async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json")
    active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active:
        await update.message.reply_text(premium("NO STOCK")+"\nAgent checking avl $ small...", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
        return
    msg=premium(f"LISTINGS {len(active)}")+"\n"
    kb=[]
    for pid,p in active[-12:][::-1]:
        msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅\n"
        kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)[str(update.effective_user.id)]
    await update.message.reply_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}\n\nUse /deposit to add", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

async def deposit_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("DEPOSIT")+"Min $5 - Choose coin:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def filter_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("FILTER")+"Choose type:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("All", callback_data="filter_all"), InlineKeyboardButton("Gift Mail", callback_data="filter_gift")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def check_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("CHECK CARD")+"Send card to check:\nEx: 451R...USD$3.39", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

async def profile_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    u=get_user(uid)[str(uid)]
    await update.message.reply_text(premium("PROFILE")+f"👤 {update.effective_user.first_name}\n🆔 {uid}\n💳 ${u.get('balance',0)}\n🛒 {len(u.get('purchases',[]))} purchases\n🏪 Vendor: {u.get('is_vendor')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 History", callback_data="my_purchases"), InlineKeyboardButton("♻️ Relist", callback_data="relist")],[InlineKeyboardButton("🏪 Vendor Dash", callback_data="top_vendor")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

async def support_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("SUPPORT & REFUND")+f"🆘 @toma 24/7\n\n↩️ REFUND RULE:\n• Invalid = Full refund 10 min\n• Valid used = No refund\n• Proof: screenshot\n\n📢 Stock: {STOCK_CHANNEL_LINK}", reply_markup=top_menu(update.effective_user.id==ADMIN_ID), disable_web_page_preview=True)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    cfg=get_cfg()
    prods=load_file("products.json")
    stock=len([x for x in prods.values() if not x.get('sold')])
    await update.message.reply_text(premium("ADMIN PANEL")+f"Perc: {cfg['perc']}% | Stock:{stock}\nChoose action:", reply_markup=admin_panel_kb())

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""
    uid=update.effective_user.id
    if txt.startswith('/'): return
    wait=context.user_data.get('wait')
    if wait=="add_stock":
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
        if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
        amt=float(m.group(1)) if m else 3.39
        context.user_data['pending']=txt
        context.user_data['amt']=amt
        context.user_data['wait']="set_price"
        cfg=get_cfg()
        calc=round(amt*cfg['perc']/100,2)
        await update.message.reply_text(f"Detected avl $ {amt} -> ${calc} (Perc {cfg['perc']}%)\nSend price or click Use {cfg['perc']}%", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Use {cfg['perc']}% (${calc})", callback_data="use_perc")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return
    if wait=="set_price":
        try:
            price=float(txt.replace('$','').strip())
        except:
            await update.message.reply_text("Send price e.g. 9.75")
            return
        pid=str(uuid.uuid4())[:6]
        prods=load_file("products.json")
        prods[pid]={"code":context.user_data['pending'], "avl":f"avl $ {context.user_data['amt']}", "price":price, "sold":False, "owner":uid}
        save_file("products.json", prods)
        context.user_data['wait']=None
        await update.message.reply_text(f"✅ Added {pid} avl $ {context.user_data['amt']} -> ${price} G ✅ P ✅ REG ✅", reply_markup=admin_panel_kb())
        await auto_post(context, [prods[pid]])
        return
    if wait=="add_bal":
        try:
            parts=txt.split()
            uid_t=parts[0]
            amt=float(parts[1])
            users=load_file("users.json")
            if uid_t in users:
                users[uid_t]['balance']=users[uid_t].get('balance',0)+amt
                save_file("users.json", users)
                await update.message.reply_text(f"✅ Added ${amt} to {uid_t}", reply_markup=admin_panel_kb())
            else:
                await update.message.reply_text("User not found", reply_markup=admin_panel_kb())
        except:
            await update.message.reply_text("Format: USERID AMOUNT\nEx: 7634497248 10", reply_markup=admin_panel_kb())
        context.user_data['wait']=None
        return
    if wait=="set_perc":
        try:
            perc=float(txt.replace('%',''))
            cfg=get_cfg()
            cfg['perc']=perc
            save_file("config.json", cfg)
            await update.message.reply_text(f"✅ Perc set {perc}%", reply_markup=admin_panel_kb())
        except:
            await update.message.reply_text("Send number e.g. 65")
        context.user_data['wait']=None
        return
    if "USD" in txt or "$" in txt and uid==ADMIN_ID:
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
        if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
        if m:
            amt=float(m.group(1))
            context.user_data['pending']=txt
            context.user_data['amt']=amt
            context.user_data['wait']="set_price"
            cfg=get_cfg()
            calc=round(amt*cfg['perc']/100,2)
            await update.message.reply_text(f"Detected avl $ {amt} -> ${calc} (Perc {cfg['perc']}%)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Use {cfg['perc']}%", callback_data="use_perc")]]))
            return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    d=q.data
    uid=q.from_user.id

    if d=="main_menu":
        await q.edit_message_text(welcome_text(), reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True)
        return
    if d=="top_admin":
        cfg=get_cfg()
        prods=load_file("products.json")
        stock=len([x for x in prods.values() if not x.get('sold')])
        await q.edit_message_text(premium("ADMIN PANEL")+f"Perc: {cfg['perc']}% | Stock:{stock}", reply_markup=admin_panel_kb())
        return
    if d=="top_list" or d=="filter_all":
        prods=load_file("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold')]
        if not active:
            await q.edit_message_text(premium("NO STOCK")+"Agent checking...", reply_markup=top_menu(uid==ADMIN_ID))
            return
        msg=premium(f"LISTINGS {len(active)}")+"\n"
        kb=[]
        for pid,p in active[-12:][::-1]:
            msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅\n"
            kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
        return
    if d=="filter_gift":
        prods=load_file("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold') and 'gift' in v.get('code','').lower()]
        msg=premium(f"GIFT MAIL {len(active)}")+"\n"
        kb=[]
        for pid,p in active[-12:][::-1]:
            kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        await q.edit_message_text(msg or "No gift mail", reply_markup=InlineKeyboardMarkup(kb) if kb else top_menu(uid==ADMIN_ID))
        return
    if d=="top_bal":
        u=get_user(uid)[str(uid)]
        await q.edit_message_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}\n\nUse /deposit", reply_markup=top_menu(uid==ADMIN_ID))
        return
    if d=="top_profile":
        u=get_user(uid)[str(uid)]
        await q.edit_message_text(premium("PROFILE")+f"👤 {q.from_user.first_name}\n🆔 {uid}\n💳 ${u.get('balance',0)}\n🛒 {len(u.get('purchases',[]))}\n🏪 Vendor:{u.get('is_vendor')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 History", callback_data="my_purchases"), InlineKeyboardButton("🏪 Vendor", callback_data="top_vendor")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return
    if d=="top_dep":
        await q.edit_message_text(premium("DEPOSIT")+"Min $5 - Choose:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return
    if d=="top_filter":
        await q.edit_message_text(premium("FILTER")+"Choose:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("All", callback_data="filter_all"), InlineKeyboardButton("Gift Mail", callback_data="filter_gift")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return
    if d=="top_check":
        await q.edit_message_text(premium("CHECK CARD")+"Send card: 451R...USD$3.39", reply_markup=top_menu(uid==ADMIN_ID))
        return
    if d=="top_ref" or d=="top_redeem" or d=="top_vendor" or d=="top_agent":
        await q.edit_message_text(premium(d.upper())+f"https://t.me/{context.bot.username}?start={uid}\nVendor Sales: ${get_user(uid)[str(uid)].get('vendor_sales',0)}", reply_markup=top_menu(uid==ADMIN_ID))
        return
    if d=="top_sup" or d=="top_refund":
        await q.edit_message_text(premium("SUPPORT & REFUND")+f"🆘 @toma 24/7\n↩️ Invalid = Refund 10 min\nValid used = No refund\nProof needed\n\n📢 Stock: {STOCK_CHANNEL_LINK}", reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True)
        return
    if d=="top_channel":
        await q.edit_message_text(premium("STOCK CHANNEL")+f"📢 {STOCK_CHANNEL_LINK}\nAll new stock auto posted!", reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True)
        return
    if d=="dep_ltc":
        qr=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={LTC_ADDRESS}"
        await q.edit_message_text(premium("LTC DEPOSIT")+f"Address:\n`{LTC_ADDRESS}`\n\nMin $5", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        try: await context.bot.send_photo(chat_id=q.message.chat_id, photo=qr, caption=f"LTC QR: {LTC_ADDRESS}")
        except: pass
        return
    if d=="dep_sol":
        qr=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={SOL_ADDRESS}"
        await q.edit_message_text(premium("SOL DEPOSIT")+f"Address:\n`{SOL_ADDRESS}`\n\nMin $5", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        try: await context.bot.send_photo(chat_id=q.message.chat_id, photo=qr, caption=f"SOL QR: {SOL_ADDRESS}")
        except: pass
        return
    if d=="add_stock":
        context.user_data['wait']="add_stock"
        await q.edit_message_text("➕ Send card:\n451R4ND00M4LLV4CC...USD$3.39\nAgent will make avl $ small + G/P/REG", reply_markup=admin_panel_kb())
        return
    if d=="set_perc":
        context.user_data['wait']="set_perc"
        await q.edit_message_text("💲 Send new % e.g. 65 or 39", reply_markup=admin_panel_kb())
        return
    if d=="add_bal":
        context.user_data['wait']="add_bal"
        await q.edit_message_text("💵 Add Balance\nFormat: USERID AMOUNT\nEx: 7634497248 50", reply_markup=admin_panel_kb())
        return
    if d=="relist_admin":
        prods=load_file("products.json")
        sold=[(k,v) for k,v in prods.items() if v.get('sold')]
        if not sold:
            await q.edit_message_text("No sold to relist", reply_markup=admin_panel_kb())
            return
        msg=premium("RELIST")+"\n"
        kb=[]
        for pid,p in sold[-10:]:
            msg+=f"💎 {p['code'][:4]}... ${p['price']}\n"
            kb.append([InlineKeyboardButton(f"♻️ {p['code'][:4]}... Relist", callback_data=f"do_relist_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("do_relist_"):
        pid=d.replace("do_relist_","")
        prods=load_file("products.json")
        if pid in prods:
            prods[pid]['sold']=False
            save_file("products.json", prods)
            await q.edit_message_text(f"✅ Relisted {pid}", reply_markup=admin_panel_kb())
        return
    if d=="vendor_req":
        users=load_file("users.json")
        req=[k for k,v in users.items() if v.get('requests_vendor')]
        msg=premium("VENDOR REQ")+f"\n{len(req)} requests\n"
        kb=[]
        for uid_r in req[-10:]:
            kb.append([InlineKeyboardButton(f"✅ Approve {uid_r}", callback_data=f"app_vendor_{uid_r}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb) if len(kb)>1 else admin_panel_kb())
        return
    if d.startswith("app_vendor_"):
        uid_r=d.replace("app_vendor_","")
        users=load_file("users.json")
        if uid_r in users:
            users[uid_r]['is_vendor']=True
            users[uid_r]['requests_vendor']=False
            save_file("users.json", users)
            await q.edit_message_text(f"✅ Vendor approved {uid_r}", reply_markup=admin_panel_kb())
        return
    if d=="all_sellers":
        users=load_file("users.json")
        sellers=[(k,v) for k,v in users.items() if v.get('is_vendor')]
        msg=premium(f"ALL SELLERS {len(sellers)}")+"\n"
        for k,v in sellers[-15:]:
            msg+=f"👤 {k} Bal:${v.get('balance',0)} Sales:${v.get('vendor_sales',0)}\n"
        await q.edit_message_text(msg, reply_markup=admin_panel_kb())
        return
    if d=="orders":
        orders=load_file("orders.json")
        pend=[(k,v) for k,v in orders.items() if v.get('status')=='pending']
        msg=premium(f"PENDING {len(pend)}")+"\n"
        kb=[]
        for oid,o in pend[-10:]:
            msg+=f"⏳ {oid} Buyer:{o['buyer_id']} ${o['price']}\n"
            kb.append([InlineKeyboardButton(f"✅ {oid} Approve", callback_data=f"approve_{oid}"), InlineKeyboardButton(f"❌ Reject", callback_data=f"reject_{oid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else admin_panel_kb())
        return
    if d=="sales_hist":
        orders=load_file("orders.json")
        done=[(k,v) for k,v in orders.items() if v.get('status')=='completed']
        total=sum([v['price'] for k,v in done])
        msg=premium(f"SALES HISTORY {len(done)}")+f"\nTotal: ${total}\n"
        for oid,o in done[-10:]:
            msg+=f"✅ {oid} ${o['price']} Buyer:{o['buyer_id']}\n"
        await q.edit_message_text(msg, reply_markup=admin_panel_kb())
        return
    if d=="buyer_hist":
        users=load_file("users.json")
        msg=premium("BUYER HISTORY")+"\n"
        for uid_k,u in list(users.items())[-10:]:
            msg+=f"👤 {uid_k} Purchases:{len(u.get('purchases',[]))} Bal:${u.get('balance',0)}\n"
        await q.edit_message_text(msg, reply_markup=admin_panel_kb())
        return
    if d=="stock_info":
        prods=load_file("products.json")
        cnt=len([x for x in prods.values() if not x.get('sold')])
        await q.edit_message_text(f"📦 Stock: {cnt} cards available", reply_markup=admin_panel_kb())
        return
    if d=="post_all":
        prods=load_file("products.json")
        active=[v for v in prods.values() if not v.get('sold')][:5]
        await auto_post(context, active)
        await q.edit_message_text(f"📢 Posted {len(active)} to {STOCK_CHANNEL_LINK}", reply_markup=admin_panel_kb())
        return
    if d=="use_perc":
        cfg=get_cfg()
        amt=context.user_data.get('amt',3.39)
        calc=round(amt*cfg['perc']/100,2)
        pid=str(uuid.uuid4())[:6]
        prods=load_file("products.json")
        prods[pid]={"code":context.user_data['pending'], "avl":f"avl $ {amt}", "price":calc, "sold":False, "owner":uid}
        save_file("products.json", prods)
        context.user_data['wait']=None
        await q.edit_message_text(f"✅ Added {pid} avl $ {amt} -> ${calc} (Perc {cfg['perc']}%) G ✅ P ✅ REG ✅", reply_markup=admin_panel_kb())
        await auto_post(context, [prods[pid]])
        return
    if d.startswith("view_"):
        pid=d.replace("view_","")
        p=load_file("products.json").get(pid)
        if not p: return
        await q.edit_message_text(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} G ✅ P ✅ REG ✅\nCode hidden until buy", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy ${p['price']}", callback_data=f"buy_{pid}")],[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return
    if d=="my_purchases":
        pur=get_user(uid)[str(uid)].get('purchases',[])
        if not pur:
            await q.edit_message_text("No purchases yet", reply_markup=top_menu(uid==ADMIN_ID))
            return
        msg=premium("HISTORY")+"\n"
        for p in pur[-10:]:
            msg+=f"💎 {p.get('code','')[:8]}... ${p.get('price')}\n"
        await q.edit_message_text(msg, reply_markup=top_menu(uid==ADMIN_ID))
        return

async def run_bot():
    print("BOT INIT v36 FINAL - NO BUG")
    app=Application.builder().token(BOT_TOKEN).post_init(set_cmds).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("listings", listings_h))
    app.add_handler(CommandHandler("listing", listings_h))
    app.add_handler(CommandHandler("balance", balance_h))
    app.add_handler(CommandHandler("deposit", deposit_h))
    app.add_handler(CommandHandler("filter", filter_h))
    app.add_handler(CommandHandler("check", check_h))
    app.add_handler(CommandHandler("profile", profile_h))
    app.add_handler(CommandHandler("vendor", profile_h))
    app.add_handler(CommandHandler("support", support_h))
    app.add_handler(CallbackQueryHandler(cb_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))

    await app.initialize()
    await app.start()
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        print("Webhook deleted - Polling forced")
    except Exception as e:
        print(f"Webhook del err {e}")

    await app.updater.start_polling(drop_pending_updates=True)
    print("✅ POLLING LIVE v36 FINAL - BOT READY")
    while True:
        await asyncio.sleep(3600)

def run_thread():
    asyncio.run(run_bot())

if __name__ == "__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
