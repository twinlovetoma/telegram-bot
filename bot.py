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
def home(): return "v41 FORWARD TRX BULK LIVE"
@flask_app.route('/health')
def health(): return "OK v41"

def load_file(f, default=None):
    try:
        if os.path.exists(f):
            with open(f,'r') as x: return json.load(x)
    except: pass
    return default if default is not None else {}
def save_file(f,d):
    with open(f,'w') as x: json.dump(d,x, indent=2)
def get_user(uid):
    users=load_file("users.json"); s=str(uid)
    if s not in users: users[s]={"balance":0,"purchases":[],"is_vendor":False,"vendor_sales":0,"ref_by":None,"requests_vendor":False,"ref_earn":0}
    save_file("users.json", users); return users
def get_cfg(): c=load_file("config.json"); return c if c else {"perc":39,"comm":5}
def premium(t): return f"╔══════╗ ✨ {t} ✨ ╚══════╝\n"

def top_menu(admin=False):
    kb=[[InlineKeyboardButton("📋 Listings", callback_data="top_list"), InlineKeyboardButton("💳 Balance", callback_data="top_bal"), InlineKeyboardButton("👤 Profile", callback_data="top_profile")],
        [InlineKeyboardButton("💰 Deposit", callback_data="top_dep"), InlineKeyboardButton("⚙️ Filter", callback_data="top_filter"), InlineKeyboardButton("🔍 Check", callback_data="top_check")],
        [InlineKeyboardButton("👥 Refer", callback_data="top_ref"), InlineKeyboardButton("🔑 Redeem", callback_data="top_redeem"), InlineKeyboardButton("🏪 Vendor", callback_data="top_vendor")],
        [InlineKeyboardButton("🆘 Support", callback_data="top_sup"), InlineKeyboardButton("↩️ Refund", callback_data="top_refund"), InlineKeyboardButton("📢 Stock", callback_data="top_channel")]]
    if admin: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="top_admin")])
    return InlineKeyboardMarkup(kb)

def admin_panel_kb():
    cfg=get_cfg(); stock=len([x for x in load_file("products.json").values() if not x.get('sold')])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock:{stock}", callback_data="stock_info"), InlineKeyboardButton(f"💲 {cfg['perc']}%", callback_data="set_perc")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add_stock"), InlineKeyboardButton("📢 Post", callback_data="post_all")],
        [InlineKeyboardButton("💵 Add Balance", callback_data="add_bal"), InlineKeyboardButton("🔄 Relist", callback_data="relist_admin")],
        [InlineKeyboardButton("🧑‍💼 Vendor Req", callback_data="vendor_req"), InlineKeyboardButton("👥 All Sellers", callback_data="all_sellers")],
        [InlineKeyboardButton("⏳ Pending", callback_data="orders"), InlineKeyboardButton("📊 Sales", callback_data="sales_hist")],
        [InlineKeyboardButton("📦 Buyer History", callback_data="buyer_hist"), InlineKeyboardButton("💸 TRX Logs", callback_data="trx_logs")],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ])

def welcome_text():
    cfg=get_cfg()
    return premium("WELCOME TO PREPAIDS GIFT'S")+f"Hello! 👋\n💎 v41 Forward+TRX+Bulk Mark\nPerc {cfg['perc']}% Comm {cfg['comm']}%\n📢 {STOCK_CHANNEL_LINK}\n🆘 @toma\n👇 Top only:"

def mark_kb(g,p,reg,price,amt, is_bulk=False):
    g_txt=f"G {'🟢 ON' if g else '🔴 OFF'}"
    p_txt=f"P {'🟢 ON' if p else '🔴 OFF'}"
    reg_txt=f"{'🔵 REG' if reg else '⚪ UNREG'}"
    save_txt=f"💾 Save All ${price}" if is_bulk else f"💾 Save ${price}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(g_txt, callback_data="mark_g"), InlineKeyboardButton(p_txt, callback_data="mark_p"), InlineKeyboardButton(reg_txt, callback_data="mark_reg")],
        [InlineKeyboardButton("➖ $1", callback_data="price_minus"), InlineKeyboardButton(f"💲 ${price}", callback_data="price_custom"), InlineKeyboardButton("➕ $1", callback_data="price_plus")],
        [InlineKeyboardButton(save_txt, callback_data="mark_save"), InlineKeyboardButton("❌ Cancel", callback_data="top_admin")],
        [InlineKeyboardButton("➕ Add Next", callback_data="add_stock")]
    ])

# --- NEW: Parse forward with TRX ---
def parse_forward_cards(text):
    # Find all cards like 4511... USD$25 or 4511... $25 or 4511XXXXX
    cards = re.findall(r'\b\d{4,6}[\dX]{6,}\S*?USD\$?\s*\d+(?:\.\d+)?|\b\d{13,19}X+\b|\b\d{12,19}\b.*?\$\d+', text, re.I)
    # Better fallback: lines containing USD$
    if not cards:
        cards = [line.strip() for line in text.splitlines() if 'USD' in line.upper() or re.search(r'\d{12,}', line)]
    # Clean
    cards = [c.strip() for c in cards if len(c.strip())>10][:10] # max 10 bulk
    # TRX detection
    trx_match = re.search(r'(?:TRX|TXID|Transaction|Hash)[:\s]*([A-Za-z0-9]{6,})', text, re.I)
    trx_id = trx_match.group(1) if trx_match else None
    # Amount from TRX line
    amt_match = re.search(r'TRX.*?\$?\s*(\d+(?:\.\d+)?)', text, re.I)
    trx_amt = amt_match.group(1) if amt_match else None
    return cards, trx_id, trx_amt

async def set_cmds(app):
    cmds=[BotCommand("start","🏠 Welcome"),BotCommand("listings","📋 Browse"),BotCommand("balance","💳 Balance"),BotCommand("deposit","💰 Deposit"),BotCommand("filter","⚙️ Filter"),BotCommand("check","🔍 Check"),BotCommand("profile","👤 Profile"),BotCommand("vendor","🏪 Vendor"),BotCommand("refer","👥 Refer"),BotCommand("redeem","🔑 Redeem"),BotCommand("support","🆘 Support"),BotCommand("admin","👑 Admin")]
    try: await app.bot.set_my_commands(cmds)
    except: pass

async def auto_post(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium("NEW STOCK")+"\n"
        for p in prods: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} {p.get('g_txt','')} {p.get('p_txt','')} {p.get('reg_txt','')}\n"
        cid=int(STOCK_CHANNEL_ID) if STOCK_CHANNEL_ID.lstrip('-').isdigit() else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=cid, text=msg)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=get_user(update.effective_user.id); s=str(update.effective_user.id)
    if context.args:
        ref=str(context.args[0])
        if s in users and users[s].get('ref_by') is None and ref!=s and ref in users:
            users[s]['ref_by']=ref; save_file("users.json", users)
    await update.message.reply_text(welcome_text(), reply_markup=top_menu(update.effective_user.id==ADMIN_ID), disable_web_page_preview=True)

async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text(premium("NO STOCK"), reply_markup=top_menu(update.effective_user.id==ADMIN_ID)); return
    msg=premium(f"LISTINGS {len(active)}")+"\n"; kb=[]
    for pid,p in active[-12:][::-1]: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} {p.get('g_txt','')} {p.get('p_txt','')} {p.get('reg_txt','')}\n"; kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... ${p['price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("🏠 Main", callback_data="main_menu")]); await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))
async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)[str(update.effective_user.id)]; await update.message.reply_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
async def deposit_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("DEPOSIT"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]]))
async def filter_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("All", callback_data="filter_all")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]]))
async def check_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wait']="check_card"; await update.message.reply_text(premium("CHECK")+"Send card:", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
async def profile_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u=get_user(update.effective_user.id)[str(update.effective_user.id)]; await update.message.reply_text(premium("PROFILE")+f"💳 ${u.get('balance',0)} 🛒 {len(u.get('purchases',[]))}", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
async def support_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium("SUPPORT")+f"🆘 @toma\n📢 {STOCK_CHANNEL_LINK}", reply_markup=top_menu(update.effective_user.id==ADMIN_ID), disable_web_page_preview=True)
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    await update.message.reply_text(premium("ADMIN PANEL v41"), reply_markup=admin_panel_kb())
async def refer_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; await update.message.reply_text(premium("REFER")+f"https://t.me/{context.bot.username}?start={uid}", reply_markup=top_menu(uid==ADMIN_ID))
async def redeem_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wait']="redeem"; await update.message.reply_text(premium("REDEEM")+"Send code:", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text or ""; uid=update.effective_user.id
    if txt.startswith('/'): return
    wait=context.user_data.get('wait')

    # --- FORWARD / TRX DETECTION ---
    if wait=="add_stock" or update.message.forward_from or update.message.forward_from_chat or len(txt.splitlines())>1:
        cards, trx_id, trx_amt = parse_forward_cards(txt)
        if len(cards)>=1:
            # If bulk
            if len(cards)>1:
                context.user_data['pending_codes']=cards
                context.user_data['pending_trx']=trx_id
                context.user_data['pending_trx_amt']=trx_amt
                # Use first card amount for price calc
                m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', cards[0], re.I)
                amt=float(m.group(1)) if m else 25
                cfg=get_cfg(); calc=round(amt*cfg['perc']/100,2)
                context.user_data['pending_code']=cards[0]
                context.user_data['pending_amt']=amt
                context.user_data['pending_price']=calc
                context.user_data['mark_g']=False; context.user_data['mark_p']=False; context.user_data['mark_reg']=False
                context.user_data['wait']="marking_bulk"
                await update.message.reply_text(premium("FORWARD BULK DETECTED v41")+f"📥 {len(cards)} cards found!\n💸 TRX: {trx_id or 'N/A'} ${trx_amt or ''}\n\nFirst card: {cards[0][:30]}...\navl $ {amt} -> ${calc}\n\nMark G/P/REG (will apply to ALL {len(cards)} cards):", reply_markup=mark_kb(False,False,False,calc,amt, is_bulk=True))
                return
            else:
                # Single card from forward
                txt=cards[0] # replace txt with parsed card

    if wait=="add_stock":
        m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', txt, re.I)
        if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', txt)
        amt=float(m.group(1)) if m else 25
        cfg=get_cfg(); calc=round(amt*cfg['perc']/100,2)
        context.user_data['pending_code']=txt
        context.user_data['pending_amt']=amt
        context.user_data['pending_price']=calc
        context.user_data['pending_codes']=[txt]
        context.user_data['mark_g']=False; context.user_data['mark_p']=False; context.user_data['mark_reg']=False
        context.user_data['wait']="marking"
        await update.message.reply_text(premium("MARK G/P/REG v41")+f"Card: {txt[:25]}...\navl $ {amt} -> ${calc}\n\nMark:", reply_markup=mark_kb(False,False,False,calc,amt))
        return

    if wait=="set_price":
        try: price=float(txt.replace('$','').strip())
        except: await update.message.reply_text("Send price e.g. 8.5"); return
        context.user_data['pending_price']=price
        g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False)
        amt=context.user_data['pending_amt']
        context.user_data['wait']="marking" if context.user_data.get('wait')!="marking_bulk" else "marking_bulk"
        is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await update.message.reply_text(premium("MARK")+f"Price ${price}\nCard: {context.user_data['pending_code'][:20]}...\navl $ {amt}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk))
        return

    if wait=="add_bal":
        try:
            parts=txt.split(); uid_t=parts[0]; amt=float(parts[1]); users=load_file("users.json")
            if uid_t in users: users[uid_t]['balance']=users[uid_t].get('balance',0)+amt; save_file("users.json", users); await update.message.reply_text(f"✅ Added ${amt} to {uid_t}", reply_markup=admin_panel_kb())
            else: await update.message.reply_text("User not found", reply_markup=admin_panel_kb())
        except: await update.message.reply_text("Format: USERID AMOUNT", reply_markup=admin_panel_kb())
        context.user_data['wait']=None; return
    if wait=="set_perc":
        try: perc=float(txt.replace('%','')); cfg=get_cfg(); cfg['perc']=perc; save_file("config.json", cfg); await update.message.reply_text(f"✅ Perc {perc}%", reply_markup=admin_panel_kb())
        except: await update.message.reply_text("Send e.g. 65")
        context.user_data['wait']=None; return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id
    if d=="main_menu": await q.edit_message_text(welcome_text(), reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="top_admin": await q.edit_message_text(premium("ADMIN PANEL v41"), reply_markup=admin_panel_kb()); return
    if d=="top_list" or d=="filter_all":
        prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
        if not active: await q.edit_message_text(premium("NO STOCK"), reply_markup=top_menu(uid==ADMIN_ID)); return
        msg=premium(f"LISTINGS {len(active)}")+"\n"; kb=[]
        for pid,p in active[-12:][::-1]: msg+=f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} {p.get('g_txt','')} {p.get('p_txt','')} {p.get('reg_txt','')}\n"; kb.append([InlineKeyboardButton(f"💎 {p['code'][:4]}... ${p['price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("🏠 Main", callback_data="main_menu")]); await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="top_bal": u=get_user(uid)[str(uid)]; await q.edit_message_text(premium("BALANCE")+f"💳 ${u.get('balance',0)}", reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_dep": await q.edit_message_text(premium("DEPOSIT"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return
    if d=="top_profile": await q.edit_message_text(premium("PROFILE"), reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_filter": await q.edit_message_text(premium("FILTER"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("All", callback_data="filter_all")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return
    if d=="top_check": context.user_data['wait']="check_card"; await q.edit_message_text(premium("CHECK")+"Send card:", reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_ref": await q.edit_message_text(premium("REFER")+f"https://t.me/{context.bot.username}?start={uid}", reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_redeem": context.user_data['wait']="redeem"; await q.edit_message_text(premium("REDEEM")+"Send code:", reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_vendor": await q.edit_message_text(premium("VENDOR"), reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="top_sup" or d=="top_refund": await q.edit_message_text(premium("SUPPORT")+f"🆘 @toma\n📢 {STOCK_CHANNEL_LINK}", reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="top_channel": await q.edit_message_text(premium("STOCK")+f"{STOCK_CHANNEL_LINK}", reply_markup=top_menu(uid==ADMIN_ID), disable_web_page_preview=True); return
    if d=="dep_ltc": await q.edit_message_text(premium("LTC")+f"`{LTC_ADDRESS}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return
    if d=="dep_sol": await q.edit_message_text(premium("SOL")+f"`{SOL_ADDRESS}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return

    if d=="mark_g":
        context.user_data['mark_g']=not context.user_data.get('mark_g',False)
        g=context.user_data['mark_g']; p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False)
        amt=context.user_data['pending_amt']; price=context.user_data['pending_price']; is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await q.edit_message_text(premium("MARK")+f"Card: {context.user_data['pending_code'][:25]}...\navl $ {amt} -> ${price}\nG {'🟢 ON' if g else '🔴 OFF'} P {'🟢 ON' if p else '🔴 OFF'} REG {'🔵 REG' if reg else '⚪ UNREG'}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk)); return
    if d=="mark_p":
        context.user_data['mark_p']=not context.user_data.get('mark_p',False)
        g=context.user_data.get('mark_g',False); p=context.user_data['mark_p']; reg=context.user_data.get('mark_reg',False)
        amt=context.user_data['pending_amt']; price=context.user_data['pending_price']; is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await q.edit_message_text(premium("MARK")+f"Card: {context.user_data['pending_code'][:25]}...\navl $ {amt} -> ${price}\nG {'🟢 ON' if g else '🔴 OFF'} P {'🟢 ON' if p else '🔴 OFF'} REG {'🔵 REG' if reg else '⚪ UNREG'}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk)); return
    if d=="mark_reg":
        context.user_data['mark_reg']=not context.user_data.get('mark_reg',False)
        g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data['mark_reg']
        amt=context.user_data['pending_amt']; price=context.user_data['pending_price']; is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await q.edit_message_text(premium("MARK")+f"Card: {context.user_data['pending_code'][:25]}...\navl $ {amt} -> ${price}\nG {'🟢 ON' if g else '🔴 OFF'} P {'🟢 ON' if p else '🔴 OFF'} REG {'🔵 REG' if reg else '⚪ UNREG'}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk)); return
    if d=="price_minus":
        context.user_data['pending_price']=max(0.5, round(context.user_data.get('pending_price',9)-1,2))
        g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False)
        amt=context.user_data['pending_amt']; price=context.user_data['pending_price']; is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await q.edit_message_text(premium("MARK")+f"Card: {context.user_data['pending_code'][:25]}...\navl $ {amt} -> ${price}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk)); return
    if d=="price_plus":
        context.user_data['pending_price']=round(context.user_data.get('pending_price',9)+1,2)
        g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False)
        amt=context.user_data['pending_amt']; price=context.user_data['pending_price']; is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await q.edit_message_text(premium("MARK")+f"Card: {context.user_data['pending_code'][:25]}...\navl $ {amt} -> ${price}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk)); return
    if d=="price_custom":
        context.user_data['wait']="set_price"
        await q.edit_message_text("💲 Send custom price e.g. 8.5", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Mark", callback_data="back_mark")]])); return
    if d=="back_mark":
        g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False)
        amt=context.user_data['pending_amt']; price=context.user_data['pending_price']; is_bulk=len(context.user_data.get('pending_codes',[]))>1
        await q.edit_message_text(premium("MARK")+f"Card: {context.user_data['pending_code'][:25]}...\navl $ {amt} -> ${price}", reply_markup=mark_kb(g,p,reg,price,amt, is_bulk)); return

    if d=="mark_save":
        g=context.user_data.get('mark_g',False); p=context.user_data.get('mark_p',False); reg=context.user_data.get('mark_reg',False)
        price=context.user_data['pending_price']; codes=context.user_data.get('pending_codes',[context.user_data['pending_code']])
        trx_id=context.user_data.get('pending_trx'); prods=load_file("products.json")
        saved=[]
        for code in codes:
            m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', code, re.I)
            amt=float(m.group(1)) if m else context.user_data['pending_amt']
            pid=str(uuid.uuid4())[:6]
            prods[pid]={"code":code, "avl":f"avl $ {amt}", "price":price, "sold":False, "owner":uid,
                        "g_txt":f"G {'🟢' if g else '🔴'}", "p_txt":f"P {'🟢' if p else '🔴'}", "reg_txt":f"{'🔵 REG' if reg else '⚪ UNREG'}", "trx":trx_id}
            saved.append(prods[pid]); saved[-1]['pid']=pid
        save_file("products.json", prods)
        # Save TRX log
        if trx_id:
            logs=load_file("trx_logs.json")
            logs[str(uuid.uuid4())[:6]]={"trx":trx_id, "cards":len(codes), "amount":context.user_data.get('pending_trx_amt'), "by":uid, "time":str(asyncio.get_event_loop().time())}
            save_file("trx_logs.json", logs)
        context.user_data['wait']=None
        await q.edit_message_text(f"✅ Saved {len(codes)} cards! TRX: {trx_id or 'N/A'}\nPrice ${price} G {'🟢' if g else '🔴'} P {'🟢' if p else '🔴'} REG {'🔵' if reg else '⚪'}\n\nNext?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Next", callback_data="add_stock")],[InlineKeyboardButton("👑 Admin Panel", callback_data="top_admin")]]))
        await auto_post(context, saved[:5]); return

    if d=="add_stock": context.user_data['wait']="add_stock"; await q.edit_message_text("➕ Send card or Forward with TRX:\n451129XXXXXUSD$25\nor forward message with TRX ID\n\nExample forward:\n451129...USD$25\n451130...USD$40\nTRX: abc123 $65", reply_markup=admin_panel_kb()); return
    if d=="set_perc": context.user_data['wait']="set_perc"; await q.edit_message_text("💲 Send % e.g. 65", reply_markup=admin_panel_kb()); return
    if d=="add_bal": context.user_data['wait']="add_bal"; await q.edit_message_text("💵 USERID AMOUNT", reply_markup=admin_panel_kb()); return
    if d=="relist_admin":
        prods=load_file("products.json"); sold=[(k,v) for k,v in prods.items() if v.get('sold')]
        if not sold: await q.edit_message_text("No sold", reply_markup=admin_panel_kb()); return
        msg=premium("RELIST")+"\n"; kb=[]
        for pid,p in sold[-10:]: msg+=f"💎 {p['code'][:4]}... ${p['price']}\n"; kb.append([InlineKeyboardButton(f"♻️ {p['code'][:4]} Relist", callback_data=f"do_relist_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")]); await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("do_relist_"): pid=d.replace("do_relist_",""); prods=load_file("products.json"); prods[pid]['sold']=False; save_file("products.json", prods); await q.edit_message_text(f"✅ Relisted {pid}", reply_markup=admin_panel_kb()); return
    if d=="vendor_req":
        users=load_file("users.json"); req=[k for k,v in users.items() if v.get('requests_vendor')]; kb=[]
        for uid_r in req[-10:]: kb.append([InlineKeyboardButton(f"✅ {uid_r}", callback_data=f"app_vendor_{uid_r}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="top_admin")]); await q.edit_message_text(premium("VENDOR REQ"), reply_markup=InlineKeyboardMarkup(kb) if kb else admin_panel_kb()); return
    if d.startswith("app_vendor_"): uid_r=d.replace("app_vendor_",""); users=load_file("users.json"); users[uid_r]['is_vendor']=True; users[uid_r]['requests_vendor']=False; save_file("users.json", users); await q.edit_message_text(f"✅ Vendor {uid_r}", reply_markup=admin_panel_kb()); return
    if d=="all_sellers": await q.edit_message_text(premium("SELLERS"), reply_markup=admin_panel_kb()); return
    if d=="orders": await q.edit_message_text(premium("PENDING 0"), reply_markup=admin_panel_kb()); return
    if d=="sales_hist": await q.edit_message_text(premium("SALES"), reply_markup=admin_panel_kb()); return
    if d=="buyer_hist": await q.edit_message_text(premium("BUYER HISTORY"), reply_markup=admin_panel_kb()); return
    if d=="trx_logs":
        logs=load_file("trx_logs.json")
        msg=premium(f"TRX LOGS {len(logs)}")+"\n"
        for k,v in list(logs.items())[-10:][::-1]: msg+=f"💸 {v.get('trx')} | {v.get('cards')} cards | ${v.get('amount')} by {v.get('by')}\n"
        await q.edit_message_text(msg or "No TRX logs", reply_markup=admin_panel_kb()); return
    if d=="stock_info": await q.edit_message_text(f"Stock: {len([x for x in load_file('products.json').values() if not x.get('sold')])}", reply_markup=admin_panel_kb()); return
    if d=="post_all": prods=load_file("products.json"); active=[v for v in prods.values() if not v.get('sold')][:5]; await auto_post(context, active); await q.edit_message_text(f"📢 Posted {len(active)}", reply_markup=admin_panel_kb()); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); p=load_file("products.json").get(pid)
        if not p: return
        await q.edit_message_text(f"💎 {p['code'][:4]}... {p['avl']} ${p['price']} {p.get('g_txt','')} {p.get('p_txt','')} {p.get('reg_txt','')}\nTRX: {p.get('trx','N/A')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy ${p['price']}", callback_data=f"buy_{pid}")],[InlineKeyboardButton("🏠 Main", callback_data="main_menu")]])); return
    if d.startswith("buy_"):
        pid=d.replace("buy_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get('sold'): await q.edit_message_text("❌ Sold!", reply_markup=top_menu(uid==ADMIN_ID)); return
        users=load_file("users.json"); s=str(uid); bal=users[s].get('balance',0)
        if bal < p['price']: await q.edit_message_text(f"❌ Need ${p['price']} Bal ${bal}", reply_markup=top_menu(uid==ADMIN_ID)); return
        users[s]['balance']=bal-p['price']; prods[pid]['sold']=True; owner=str(p.get('owner'));
        if owner in users: users[owner]['balance']=users[owner].get('balance',0)+p['price']*0.95
        users[s]['purchases'].append({"code":p['code'], "price":p['price']}); save_file("users.json", users); save_file("products.json", prods)
        await q.edit_message_text(premium("DELIVERED")+f"`{p['code']}`\n{p['avl']} {p.get('g_txt','')} {p.get('p_txt','')} {p.get('reg_txt','')}\nTRX: {p.get('trx','')}", parse_mode='Markdown', reply_markup=top_menu(uid==ADMIN_ID)); return

async def run_bot():
    print("BOT INIT v41 FORWARD TRX BULK")
    app=Application.builder().token(BOT_TOKEN).post_init(set_cmds).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("listings", listings_h))
    app.add_handler(CommandHandler("balance", balance_h))
    app.add_handler(CommandHandler("deposit", deposit_h))
    app.add_handler(CommandHandler("filter", filter_h))
    app.add_handler(CommandHandler("check", check_h))
    app.add_handler(CommandHandler("profile", profile_h))
    app.add_handler(CommandHandler("support", support_h))
    app.add_handler(CommandHandler("refer", refer_h))
    app.add_handler(CommandHandler("redeem", redeem_h))
    app.add_handler(CallbackQueryHandler(cb_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    await app.initialize(); await app.start()
    try: await app.bot.delete_webhook(drop_pending_updates=True)
    except: pass
    await app.updater.start_polling(drop_pending_updates=True)
    print("✅ POLLING LIVE v41 FORWARD TRX")
    while True: await asyncio.sleep(3600)

def run_thread(): asyncio.run(run_bot())
if __name__ == "__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000)))
