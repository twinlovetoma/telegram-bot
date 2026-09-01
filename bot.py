import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
STOCK_CHANNEL_LINK = os.getenv("STOCK_CHANNEL_LINK", "https://t.me/prepaidsgift")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1qYourLTC")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "So1YourSOL")
VENDOR_PRICE = 15 # Vendor access price $15

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v48 VENDOR FIX LIVE"
@flask_app.route('/health')
def health(): return "OK v48"

def load_file(f, d=None):
    try:
        if os.path.exists(f):
            with open(f,'r') as x: return json.load(x)
    except: pass
    return d if d is not None else {}
def save_file(f,d):
    with open(f,'w') as x: json.dump(d,x, indent=2)

def get_user(uid):
    users=load_file("users.json")
    s=str(uid)
    if s not in users:
        users[s]={"balance":0,"purchases":[],"is_vendor":False,"vendor_sales":0,"ref_by":None,"requests_vendor":False,"ref_earn":0}
        save_file("users.json", users)
    return users

def get_cfg(): return load_file("config.json") or {"perc":39,"comm":5}

def top_menu(admin=False):
    kb=[
        [InlineKeyboardButton("📋 Listings", callback_data="top_list"), InlineKeyboardButton("⚙️ Filter", callback_data="top_filter")],
        [InlineKeyboardButton("💰 Deposit", callback_data="top_dep"), InlineKeyboardButton("👤 Profile", callback_data="top_profile")],
    ]
    if admin: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="top_admin")])
    return InlineKeyboardMarkup(kb)

def admin_panel_kb():
    cfg=get_cfg(); stock=len([x for x in load_file("products.json").values() if not x.get('sold')])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock:{stock}", callback_data="stock_info"), InlineKeyboardButton(f"$ Set {cfg['perc']}%", callback_data="set_perc")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add_stock"), InlineKeyboardButton("📢 Post Channel", callback_data="post_all")],
        [InlineKeyboardButton("💵 Add Balance", callback_data="add_bal"), InlineKeyboardButton("🔄 Relist", callback_data="relist_admin")],
        [InlineKeyboardButton("🧑‍💼 Vendor Req", callback_data="vendor_req"), InlineKeyboardButton("👥 All Sellers", callback_data="all_sellers")],
        [InlineKeyboardButton("⏳ Pending Orders", callback_data="pending_cod"), InlineKeyboardButton("📊 Sales History", callback_data="sales_history")],
        [InlineKeyboardButton("📦 Buyer History", callback_data="buyer_history")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ])

def vendor_kb(is_vendor, balance):
    if is_vendor:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Stock", callback_data="add_stock"), InlineKeyboardButton("📦 My Stock", callback_data="my_vendor_stock")],
            [InlineKeyboardButton("💰 My Sales", callback_data="vendor_sales"), InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 Buy Vendor Access - ${VENDOR_PRICE}", callback_data="buy_vendor")],
            [InlineKeyboardButton(f"💰 Balance: ${balance} - Deposit", callback_data="top_dep")],
            [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
        ])

def welcome_text():
    cfg=get_cfg()
    return f"✨ WELCOME TO PREPAIDS GIFT'S ✨\n\nHello! 👋\nUse Menu (☰) - All buttons working!\n\nPerc {cfg['perc']}% Comm {cfg['comm']}%\n📢 {STOCK_CHANNEL_LINK}\n🆘 @toma"

def mark_kb(g,p,reg,price,amt, is_bulk=False, cat="Giftcard"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'🟢 ON' if g else '🔴 OFF'}", callback_data="mark_g"), InlineKeyboardButton(f"P {'🟢 ON' if p else '🔴 OFF'}", callback_data="mark_p"), InlineKeyboardButton(f"{'🔵 REG' if reg else '⚪ UNREG'}", callback_data="mark_reg")],
        [InlineKeyboardButton("➖ $1", callback_data="price_minus"), InlineKeyboardButton(f"💲 ${price}", callback_data="price_custom"), InlineKeyboardButton("➕ $1", callback_data="price_plus")],
        [InlineKeyboardButton(f"📂 {cat}", callback_data="noop"), InlineKeyboardButton(f"💾 Save ${price}", callback_data="mark_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="top_admin")]
    ])

def parse_forward_cards(text):
    cards = re.findall(r'\b\d{4,6}[\dX]{6,}\S*?USD\$?\s*\d+(?:\.\d+)?', text, re.I)
    if not cards: cards = [line.strip() for line in text.splitlines() if 'USD' in line.upper() and len(line.strip())>10]
    cards = [c.strip() for c in cards if len(c.strip())>10][:10]
    trx_match = re.search(r'(?:TRX|TXID|Transaction|Hash)[:\s]*([A-Za-z0-9]{6,})', text, re.I)
    trx_id = trx_match.group(1) if trx_match else None
    return cards, trx_id

async def set_cmds(app):
    cmds=[
        BotCommand("start","🚀 Launch bot"),
        BotCommand("listings","📋 Browse - Listings"),
        BotCommand("filter","⚙️ Filter - Giftcard / COD 880 CP"),
        BotCommand("profile","👤 View profile"),
        BotCommand("balance","💳 View balance"),
        BotCommand("deposit","💰 Deposit - LTC SOL"),
        BotCommand("vendor","🏪 Vendor Panel - Buy Access"),
        BotCommand("admin","👑 Admin Panel"),
        BotCommand("refer","👥 Refer 5% Earn"),
        BotCommand("redeem","🔑 Redeem Code"),
        BotCommand("support","🆘 Support"),
        BotCommand("check","🔍 Check Card"),
    ]
    try: await app.bot.set_my_commands(cmds)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    await update.message.reply_text(welcome_text(), reply_markup=top_menu(update.effective_user.id==ADMIN_ID), disable_web_page_preview=True)

async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text("NO STOCK yet", reply_markup=top_menu(update.effective_user.id==ADMIN_ID)); return
    msg=f"📋 BROWSE - LISTINGS {len(active)}\n\n"; kb=[]
    for pid,p in active[-10:][::-1]: msg+=f"💎 {p['code'][:12]}.. {p['avl']} ${p['price']}\n"; kb.append([InlineKeyboardButton(f"💎 {p['code'][:6]} ${p['price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("⚙️ Filter", callback_data="top_filter"), InlineKeyboardButton("🏠 Start", callback_data="main_menu")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def filter_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 All", callback_data="filter_All"), InlineKeyboardButton("🎁 Giftcard", callback_data="filter_Giftcard")],[InlineKeyboardButton("🎯 COD 880 CP", callback_data="filter_COD"), InlineKeyboardButton("🛒 Amazon", callback_data="filter_Amazon")],[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
    await update.message.reply_text("🎯 FILTER - Giftcard vs COD 880 CP", reply_markup=kb)

async def profile_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; users=get_user(uid); u=users.get(str(uid),{}); name=update.effective_user.first_name; bal=u.get('balance',0)
    is_vendor="✅ Active" if u.get('is_vendor') else "❌ Not Active - Buy in Vendor Panel"
    text=f"👤 VIEW PROFILE - WORKING ✅\n\n👤 {name}\n🆔 {uid}\n💳 Balance: ${bal}\n🛒 Buy: {len(u.get('purchases',[]))}\n🏪 Vendor: {is_vendor}"
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("📜 My Purchases", callback_data="my_purchases")],[InlineKeyboardButton("🏪 Vendor Panel", callback_data="vendor_panel")],[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]])
    await update.message.reply_text(text, reply_markup=kb)

async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id); u=load_file("users.json").get(str(update.effective_user.id),{})
    await update.message.reply_text(f"💳 VIEW BALANCE - WORKING ✅\n\nBalance: ${u.get('balance',0)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Deposit", callback_data="top_dep")],[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]))

async def deposit_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💰 DEPOSIT - WORKING ✅\n\nLTC: `{LTC_ADDRESS}`\nSOL: `{SOL_ADDRESS}`\n\nMin $5 - TRX ID send to @toma", parse_mode='Markdown', reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

# --- VENDOR PANEL FIX ---
async def vendor_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; users=get_user(uid); u=users.get(str(uid),{}); bal=u.get('balance',0); is_vendor=u.get('is_vendor',False)
    if is_vendor:
        prods=load_file("products.json"); my=len([p for p in prods.values() if p.get('owner')==uid and not p.get('sold')])
        text=f"🏪 VENDOR PANEL - ACTIVE ✅\n\nYour Stock: {my}\nSales: {u.get('vendor_sales',0)}\nBalance: ${bal}\n\nYou can add Giftcard & COD 880 CP stock!"
        await update.message.reply_text(text, reply_markup=vendor_kb(True, bal))
    else:
        text=f"🏪 VENDOR PANEL - BUY ACCESS\n\n💰 Price: ${VENDOR_PRICE}\n💳 Your Balance: ${bal}\n\nBenefits:\n✅ Add Giftcard full code (4511...USD$)\n✅ Add COD 880 CP listing\n✅ Earn {get_cfg()['comm']}% commission\n✅ Auto post to channel\n\nBuy korle instant active!"
        await update.message.reply_text(text, reply_markup=vendor_kb(False, bal))

async def admin_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: await update.message.reply_text("❌ Admin only"); return
    await update.message.reply_text("👑 ADMIN PANEL - WORKING ✅", reply_markup=admin_panel_kb())

async def refer_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    await update.message.reply_text(f"👥 REFER 5% - WORKING ✅\nLink: https://t.me/prepaidsgift_bot?start={uid}", reply_markup=top_menu(uid==ADMIN_ID))

async def redeem_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔑 REDEEM - Send code", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
    context.user_data['wait']="redeem"

async def support_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 SUPPORT - @toma\n"+STOCK_CHANNEL_LINK, reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

async def check_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 CHECK CARD - Send card", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""; uid=update.effective_user.id
    if txt.startswith('/'): return
    wait=context.user_data.get('wait')
    if wait and wait.startswith("activate_"):
        oid=wait.replace("activate_",""); orders=load_file("orders.json")
        if oid in orders:
            orders[oid]['activation']=txt; orders[oid]['status']='pending_activation'; save_file("orders.json", orders)
            await update.message.reply_text(f"Your order was processing we notify you after complete ✅\n\nOrder ID: {oid}\n🔑 {txt}\n⏳ 10-15 min wait", parse_mode='Markdown', reply_markup=top_menu(uid==ADMIN_ID))
            try:
                kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve", callback_data=f"approve_cod_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_cod_{oid}")]])
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 COD ACTIVATION {oid}\nBuyer {uid}\n🎯 {orders[oid]['brand']}\n🔑 {txt}\n💰 ${orders[oid]['price']}", reply_markup=kb)
            except: pass
        context.user_data['wait']=None; return
    if wait=="add_cod_title":
        title=txt; context.user_data['pending_code']=title; context.user_data['pending_amt']=10; context.user_data['pending_price']=10; context.user_data['pending_codes']=[title]; context.user_data['upload_type']="COD"; context.user_data['mark_g']=False; context.user_data['mark_p']=False; context.user_data['mark_reg']=False; context.user_data['wait']="marking"
        await update.message.reply_text(f"🎯 COD: {title}", reply_markup=mark_kb(False,False,False,10,10,False,"COD")); return
    if wait=="add_stock" or len(txt.splitlines())>1:
        cards, trx_id = parse_forward_cards(txt)
        if len(cards)>=1 and "COD" not in txt.upper() and "880" not in txt:
            if len(cards)>1:
                context.user_data['pending_codes']=cards; context.user_data['pending_trx']=trx_id; m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', cards[0], re.I); amt=float(m.group(1)) if m else 25; cfg=get_cfg(); calc=round(amt*cfg['perc']/100,2)
                context.user_data['pending_code']=cards[0]; context.user_data['pending_amt']=amt; context.user_data['pending_price']=calc; context.user_data['upload_type']="Giftcard"; context.user_data['mark_g']=False; context.user_data['mark_p']=False; context.user_data['mark_reg']=False; context.user_data['wait']="marking_bulk"
                await update.message.reply_text(f"📥 BULK {len(cards)} TRX:{trx_id or 'N/A'}", reply_markup=mark_kb(False,False,False,calc,amt, True, "Giftcard")); return
            else: txt=cards[0]
    if wait=="add_stock":
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I); amt=float(m.group(1)) if m else 25; cfg=get_cfg(); calc=round(amt*cfg['perc']/100,2)
        context.user_data['pending_code']=txt; context.user_data['pending_amt']=amt; context.user_data['pending_price']=calc; context.user_data['pending_codes']=[txt]; context.user_data['upload_type']="Giftcard"; context.user_data['mark_g']=False; context.user_data['mark_p']=False; context.user_data['mark_reg']=False; context.user_data['wait']="marking"
        await update.message.reply_text(f"🎁 Giftcard: {txt[:25]}... ${calc}", reply_markup=mark_kb(False,False,False,calc,amt,False,"Giftcard")); return
    if wait=="set_price":
        try: price=float(txt.replace('$',''))
        except: await update.message.reply_text("Send price e.g. 8.5"); return
        context.user_data['pending_price']=price; g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False); amt=context.user_data['pending_amt']; cat=context.user_data.get('upload_type',"Giftcard"); is_bulk=len(context.user_data.get('pending_codes',[]))>1
        context.user_data['wait']="marking_bulk" if is_bulk else "marking"
        await update.message.reply_text(f"Price ${price}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk, cat)); return
    if wait=="add_bal":
        try: parts=txt.split(); uid_t=parts[0]; amt=float(parts[1]); users=load_file("users.json"); users[uid_t]['balance']=users[uid_t].get('balance',0)+amt; save_file("users.json", users); await update.message.reply_text(f"✅ Added ${amt}", reply_markup=admin_panel_kb())
        except: await update.message.reply_text("Format: USERID AMOUNT", reply_markup=admin_panel_kb())
        context.user_data['wait']=None; return
    if wait=="set_perc":
        try: perc=float(txt.replace('%','')); cfg=get_cfg(); cfg['perc']=perc; save_file("config.json", cfg); await update.message.reply_text(f"✅ Perc {perc}%", reply_markup=admin_panel_kb())
        except: pass
        context.user_data['wait']=None; return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id
    users=load_file("users.json"); u=users.get(str(uid),{}); bal=u.get('balance',0)

    # VENDOR BUY FIX
    if d=="vendor_panel" or d=="vendor":
        is_vendor=u.get('is_vendor',False)
        if is_vendor:
            prods=load_file("products.json"); my=len([p for p in prods.values() if p.get('owner')==uid and not p.get('sold')])
            text=f"🏪 VENDOR PANEL - ACTIVE ✅\n\nYour Stock: {my}\nSales: {u.get('vendor_sales',0)}\nBalance: ${bal}"
            await q.edit_message_text(text, reply_markup=vendor_kb(True, bal)); return
        else:
            text=f"🏪 VENDOR PANEL - BUY ACCESS - WORKING ✅\n\n💰 Price: ${VENDOR_PRICE}\n💳 Your Balance: ${bal}\n\nBenefits:\n✅ Add Giftcard full code\n✅ Add COD 880 CP listing\n✅ Earn commission\n\nBuy korle instant active!"
            await q.edit_message_text(text, reply_markup=vendor_kb(False, bal)); return

    if d=="buy_vendor":
        if u.get('is_vendor'):
            await q.edit_message_text("✅ Already vendor! - WORKING ✅", reply_markup=vendor_kb(True, bal)); return
        if bal < VENDOR_PRICE:
            await q.edit_message_text(f"❌ Need ${VENDOR_PRICE} Balance ${bal}\n\nDeposit koro first!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Deposit", callback_data="top_dep")],[InlineKeyboardButton("⬅️ Back", callback_data="vendor_panel")]])); return
        users[str(uid)]['balance']=bal-VENDOR_PRICE; users[str(uid)]['is_vendor']=True; save_file("users.json", users)
        await q.edit_message_text(f"✅ VENDOR ACCESS BOUGHT! - WORKING ✅\n\n💳 Paid: ${VENDOR_PRICE}\n💰 New Bal: ${bal-VENDOR_PRICE}\n\nNow you can add stock!", reply_markup=vendor_kb(True, bal-VENDOR_PRICE))
        try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🎉 New Vendor! {uid} paid ${VENDOR_PRICE}")
        except: pass
        return

    if d=="my_vendor_stock":
        prods=load_file("products.json"); my=[(k,v) for k,v in prods.items() if v.get('owner')==uid and not v.get('sold')]
        msg=f"📦 My Vendor Stock {len(my)} - WORKING ✅\n"
        for pid,p in my[-10:]: msg+=f"💎 {p['code'][:10]}.. ${p['price']}\n"
        if not my: msg="No stock - Add Stock chap diye add koro"
        await q.edit_message_text(msg, reply_markup=vendor_kb(True, bal)); return

    if d=="vendor_sales":
        await q.edit_message_text(f"💰 My Sales: {u.get('vendor_sales',0)} - WORKING ✅", reply_markup=vendor_kb(True, bal)); return

    if d=="main_menu": await q.edit_message_text(welcome_text(), reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="top_admin": await q.edit_message_text("👑 ADMIN PANEL", reply_markup=admin_panel_kb()); return
    if d=="top_list":
        prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
        if not active: await q.edit_message_text("NO STOCK", reply_markup=top_menu(uid==ADMIN_ID)); return
        msg=f"📋 LISTINGS {len(active)}\n"; kb=[]
        for pid,p in active[-10:][::-1]: msg+=f"💎 {p['code'][:10]}.. ${p['price']}\n"; kb.append([InlineKeyboardButton(f"💎 {p['code'][:6]} ${p['price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("⚙️ Filter", callback_data="top_filter"), InlineKeyboardButton("🏠 Start", callback_data="main_menu")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="top_dep": await q.edit_message_text(f"💰 DEPOSIT\nLTC: `{LTC_ADDRESS}`\nSOL: `{SOL_ADDRESS}`", parse_mode='Markdown', reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_profile" or d=="profile" or d=="bal_btn":
        name=q.from_user.first_name
        text=f"👤 VIEW PROFILE - WORKING ✅\n\n👤 {name}\n🆔 {uid}\n💳 Balance: ${bal}\n🛒 Buy: {len(u.get('purchases',[]))}\n🏪 Vendor: {'✅ Active' if u.get('is_vendor') else '❌ Buy in Vendor Panel'}"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📜 My Purchases", callback_data="my_purchases")],[InlineKeyboardButton("🏪 Vendor Panel", callback_data="vendor_panel")],[InlineKeyboardButton("⬅️ Back", callback_da
