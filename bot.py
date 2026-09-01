import os, json, uuid, threading, re
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6699688350"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc_test")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "sol_test")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "17.0 ULTIMATE FIX"
@flask_app.route('/health')
def health(): return "OK"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

def load_file(f,d=None):
    if d is None: d={}
    if not os.path.exists(f): return d
    try:
        with open(f,'r') as f2: return json.load(f2)
    except: return d
def save_file(f,d):
    with open(f,'w') as f2: json.dump(d, f2, indent=2)
def get_cfg():
    default={"perc":39,"perc_enabled":True,"version":"17.0","vendor_enabled":True,"relist_enabled":True,"vendor_price":20,"relist_price":15}
    cfg=load_file("config.json", default)
    for k,v in default.items():
        if k not in cfg: cfg[k]=v
    return cfg
def get_user(uid_s):
    users=load_file("users.json")
    if uid_s not in users:
        users[uid_s]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[]}
        save_file("users.json", users)
    return users

def premium_header(t): return f"╔═══════════════╗\n 💎 {t} 💎\n╚═══════════════╝\n"

def main_reply_kb(is_admin=False):
    kb=[
        [KeyboardButton("💳 My Balance"), KeyboardButton("👤 My Profile")],
        [KeyboardButton("📋 Browse Cards"), KeyboardButton("🔍 Check Card")],
        [KeyboardButton("💰 Deposit"), KeyboardButton("💸 Withdraw")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("🔑 Redeem Code")],
        [KeyboardButton("⚙️ Filter"), KeyboardButton("🆘 Support")],
    ]
    if is_admin:
        kb.append([KeyboardButton("👑 Admin Panel"), KeyboardButton("✏️ Edit Panel")])
        kb.append([KeyboardButton("➕ Add Stock")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)

def admin_main_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Stock: {s}", callback_data="stock")],[InlineKeyboardButton("➕ Add Stock", callback_data="add")],[InlineKeyboardButton("⏳ Pending", callback_data="orders")]])

def build_gp_price_kb(ctx_data):
    c=get_cfg()
    g=ctx_data.get('g', True); pp=ctx_data.get('p', True); reg=ctx_data.get('reg', True)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'✅' if g else '📴'}", callback_data="toggle_g"), InlineKeyboardButton(f"P {'✅' if pp else '📴'}", callback_data="toggle_p"), InlineKeyboardButton(f"REGISTERED {'✅' if reg else '❌'}", callback_data="toggle_reg")],
        [InlineKeyboardButton(f"📊 {c['perc']}% ({'ON ✅' if c['perc_enabled'] else 'OFF ❌'})", callback_data="toggle_perc_add")],
        [InlineKeyboardButton(f"✅ Use {c['perc']}% Price", callback_data="use_perc"), InlineKeyboardButton("💲 Custom $9.75", callback_data="custom_price_info")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")],
    ])

def confirm_buy_kb(pid):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_buy_{pid}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_buy_{pid}")]])

async def post_to_channel(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg=premium_header("NEW STOCK")+"\n"
        for p in prods:
            first4=p['code'][:4]
            avl=p.get('avl_small', f"avl {p['amount']}")
            msg+=f"💎 `{first4}...` {avl} | Price ${p['sell_price']} | G {'✅' if p.get('g',True) else '📴'} P {'✅' if p.get('p',True) else '📴'} REG {'✅' if p.get('reg',True) else '❌'}\n"
        chat_id=int(STOCK_CHANNEL_ID) if not STOCK_CHANNEL_ID.startswith('@') else STOCK_CHANNEL_ID
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
    except Exception as e: print(f"Channel err {e}")

async def set_bot_commands(app):
    cmds=[BotCommand("start","🚀 Launch bot"),BotCommand("profile","👤 View profile"),BotCommand("balance","💳 View balance"),BotCommand("deposit","💰 Deposit"),BotCommand("listings","📋 Browse Cards"),BotCommand("filter","⚙️ Filter"),BotCommand("support","🆘 Support")]
    try: await app.bot.set_my_commands(cmds)
    except: pass

# === COMMANDS - EKHON 100% KAJ KORBE ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; get_user(str(uid))
    txt=premium_header("WELCOME") + f"Hello {update.effective_user.first_name}!\n\n💎 50+ Gift Cards\n💰 Instant Delivery\n👑 Trusted Bot\n\n👇 Use buttons below:"
    await update.message.reply_text(txt, reply_markup=main_reply_kb(uid==ADMIN_ID))
    if uid==ADMIN_ID:
        await update.message.reply_text(premium_header("ADMIN PANEL"), reply_markup=admin_main_kb())

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; users=get_user(str(uid)); u=users[str(uid)]
    await update.message.reply_text(premium_header("MY PROFILE")+f"👤 Name: {update.effective_user.first_name}\n🆔 ID: {uid}\n💳 Balance: ${u.get('balance',0)}\n🛒 Purchases: {len(u.get('purchases',[]))}", reply_markup=main_reply_kb(uid==ADMIN_ID))

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; users=get_user(str(uid))
    await update.message.reply_text(premium_header("MY BALANCE")+f"💳 Your Balance: ${users[str(uid)].get('balance',0)}\n\n💰 Deposit via LTC/SOL", reply_markup=main_reply_kb(uid==ADMIN_ID))

async def deposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium_header("DEPOSIT")+f"🪙 LTC: `{LTC_ADDRESS}`\n◎ SOL: `{SOL_ADDRESS}`\n\nMin $5 - Send screenshot to @toma", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC QR", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL QR", callback_data="dep_sol")]]), parse_mode='Markdown')

async def listings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get('sold')]
    if not active:
        await update.message.reply_text(premium_header("NO STOCK")+"❌ No cards available now!\nAdmin will add soon.", reply_markup=main_reply_kb(update.effective_user.id==ADMIN_ID))
        return
    msg=premium_header(f"BROWSE {len(active)} CARDS")+"\n"; kb=[]
    for pid,p in active[-15:][::-1]:
        first4=p['code'][:4]; avl=p.get('avl_small', f"avl {p['amount']}")
        msg+=f"💎 {first4}... {avl} ${p['sell_price']} | G {'✅' if p.get('g',True) else '📴'} P {'✅' if p.get('p',True) else '📴'} REG {'✅' if p.get('reg',True) else '❌'}\n"
        kb.append([InlineKeyboardButton(f"💎 {first4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("⚙️ Filter by Category", callback_data="show_filter")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    CATS=["All","Gift Card Mail","Free Fire","Call of Duty 880 CP","Call of Duty Gift Card","Amazon","Google Play","Other"]
    kb=[[InlineKeyboardButton(c, callback_data=f"listings_{c}")] for c in CATS]
    await update.message.reply_text(premium_header("FILTER CATEGORY"), reply_markup=InlineKeyboardMarkup(kb))

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium_header("SUPPORT")+"🆘 Contact: @toma\n⏰ 24/7 Online", reply_markup=main_reply_kb(update.effective_user.id==ADMIN_ID))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip(); uid=update.effective_user.id
    low=txt.lower()

    # === FIX: COMMANDS VIA MESSAGE HANDLER (Eita main fix) ===
    if txt.startswith('/start') or txt.startswith('/Start'):
        await start(update, context); return
    if txt.startswith('/profile'):
        await profile_cmd(update, context); return
    if txt.startswith('/balance'):
        await balance_cmd(update, context); return
    if txt.startswith('/deposit'):
        await deposit_cmd(update, context); return
    if txt.startswith('/listings'):
        await listings_cmd(update, context); return
    if txt.startswith('/filter'):
        await filter_cmd(update, context); return
    if txt.startswith('/support'):
        await support_cmd(update, context); return

    # === BOTTOM BUTTONS ===
    if "My Balance" in txt or "balance" in low:
        await balance_cmd(update, context); return
    if "My Profile" in txt or "profile" in low:
        await profile_cmd(update, context); return
    if "Browse Cards" in txt or "browse" in low:
        await listings_cmd(update, context); return
    if "Deposit" in txt:
        await deposit_cmd(update, context); return
    if "Withdraw" in txt:
        await update.message.reply_text(premium_header("WITHDRAW")+f"💸 Min $10\n📩 Contact @toma\n💳 Balance: ${get_user(str(uid))[str(uid)].get('balance',0)}", reply_markup=main_reply_kb(uid==ADMIN_ID)); return
    if "Filter" in txt:
        await filter_cmd(update, context); return
    if "Support" in txt:
        await support_cmd(update, context); return
    if "Refer" in txt:
        await update.message.reply_text(premium_header("REFER & EARN")+f"👥 Your Link:\nhttps://t.me/{context.bot.username}?start={uid}\n\n💰 Earn 5% per deposit!", reply_markup=main_reply_kb(uid==ADMIN_ID)); return
    if "Redeem" in txt:
        context.user_data['wait']="redeem"; await update.message.reply_text("🔑 Send redeem code:"); return
    if "Check Card" in txt:
        context.user_data['wait']="check_card"; await update.message.reply_text("🔍 Send code to check:"); return
    if "Add Stock" in txt and uid==ADMIN_ID:
        context.user_data['wait']="add_codes"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True
        await update.message.reply_text(premium_header("ADD STOCK")+ "Send like:\n`451R...:xx:xx:xxx:USD$3.39 USD`\nBot will make `avl $ 3.39` small + G/P/REG buttons", parse_mode='Markdown'); return
    if "Admin Panel" in txt and uid==ADMIN_ID:
        await update.message.reply_text(premium_header("ADMIN PANEL"), reply_markup=admin_main_kb()); return

    wait=context.user_data.get('wait')

    if wait=="add_codes":
        lines=[l.strip() for l in txt.splitlines() if l.strip()]; pending=[]
        for line in lines:
            m=re.search(r'USD\$?\s*(\d+(?:\.\d+)?)', line, re.I)
            if not m: m=re.search(r'avl\s*\$?\s*(\d+(?:\.\d+)?)', line, re.I)
            if not m: m=re.search(r'\$(\d+(?:\.\d+)?)', line)
            amount=float(m.group(1)) if m else 0.0
            code_part=line; idx=line.lower().find('usd')
            if idx!=-1: code_part=line[:idx].rstrip(':').strip()
            else:
                idx2=line.lower().find('avl')
                if idx2!=-1: code_part=line[:idx2].strip()
            code_part=code_part.strip().rstrip(':')
            if not code_part: code_part=line
            pending.append({"code":code_part, "amount":f"${amount}", "amount_val":amount, "brand":"Mail", "category":"Gift Card Mail", "raw":line})
        if not pending:
            await update.message.reply_text("❌ Send like: 451R...:xx:xx:xxx:USD$3.39 USD"); return
        context.user_data['pending_codes']=pending; context.user_data['wait']="add_price"
        c=get_cfg(); calc=round(pending[0]['amount_val']*c['perc']/100,2) if pending[0]['amount_val']>0 else c['perc']
        first4=pending[0]['code'][:4]
        await update.message.reply_text(f"✅ {len(pending)} code(s)\nPreview: `{first4}... avl $ {pending[0]['amount'].replace('$','').strip()} | Price ${calc}`\n\nSet G/P/REG then price:", reply_markup=build_gp_price_kb(context.user_data), parse_mode='Markdown')
        return

    if wait=="add_price":
        price_text=txt.replace('$','').strip(); c=get_cfg(); sell_price=0
        try:
            if '%' in price_text:
                perc_val=float(price_text.replace('%','')); c['perc']=perc_val; save_file("config.json", c)
                pending=context.user_data.get('pending_codes',[])
                sell_price=round(pending[0]['amount_val']*perc_val/100,2) if pending and pending[0]['amount_val']>0 else perc_val
            else: sell_price=float(price_text)
        except:
            await update.message.reply_text("Type like 9.75 or 39%"); return
        pending=context.user_data.get('pending_codes',[]); prods=load_file("products.json"); created=[]
        for p in pending:
            pid=str(uuid.uuid4())[:6]; small=f"avl $ {p['amount'].replace('$','').strip()}"
            prod={"brand":p['brand'],"amount":small,"code":p['code'],"sell_price":sell_price,"sold":False,"category":p['category'],"g":context.user_data.get('g',True),"p":context.user_data.get('p',True),"reg":context.user_data.get('reg',True),"avl_small":small}
            prods[pid]=prod; created.append(prod)
        save_file("products.json", prods)
        context.user_data['wait']=None; context.user_data['pending_codes']=None
        await update.message.reply_text(f"✅ Added {len(created)} items @ ${sell_price} with G/P/REG", reply_markup=main_reply_kb(True))
        await post_to_channel(context, created)
        return

    if wait=="redeem":
        await update.message.reply_text(f"❌ Invalid code: {txt}", reply_markup=main_reply_kb(uid==ADMIN_ID)); context.user_data['wait']=None; return
    if wait=="check_card":
        await update.message.reply_text(f"🔍 Checking {txt[:10]}... Valid ✅ (demo)", reply_markup=main_reply_kb(uid==ADMIN_ID)); context.user_data['wait']=None; return
    if wait=="addbal":
        try:
            parts=txt.split(); uid_add=parts[0]; amt=float(parts[1])
            users=load_file("users.json")
            if uid_add not in users: users[uid_add]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[]}
            users[uid_add]["balance"]=users[uid_add].get("balance",0)+amt; save_file("users.json", users)
            await update.message.reply_text(f"✅ Added ${amt} to {uid_add}")
        except: await update.message.reply_text("Format: USERID AMOUNT")
        context.user_data['wait']=None; return

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id
    if d=="add":
        context.user_data['wait']="add_codes"; context.user_data['g']=True; context.user_data['p']=True; context.user_data['reg']=True
        await q.edit_message_text(premium_header("ADD STOCK")+ "Send: `451R...:xx:xx:xxx:USD$3.39 USD`", parse_mode='Markdown'); return
    if d=="cancel_add":
        context.user_data['wait']=None; context.user_data['pending_codes']=None
        await q.edit_message_text("❌ Cancelled", reply_markup=admin_main_kb()); return
    if d=="toggle_g":
        context.user_data['g']=not context.user_data.get('g',True)
        await q.edit_message_text(f"G -> {'✅' if context.user_data['g'] else '📴'}", reply_markup=build_gp_price_kb(context.user_data)); return
    if d=="toggle_p":
        context.user_data['p']=not context.user_data.get('p',True)
        await q.edit_message_text(f"P -> {'✅' if context.user_data['p'] else '📴'}", reply_markup=build_gp_price_kb(context.user_data)); return
    if d=="toggle_reg":
        context.user_data['reg']=not context.user_data.get('reg',True)
        await q.edit_message_text(f"REG -> {'✅' if context.user_data['reg'] else '❌'}", reply_markup=build_gp_price_kb(context.user_data)); return
    if d=="toggle_perc_add":
        c=get_cfg(); c['perc_enabled']=not c.get('perc_enabled',True); save_file("config.json", c)
        await q.edit_message_text(f"Perc {c['perc']}% {'ON ✅' if c['perc_enabled'] else 'OFF ❌'}", reply_markup=build_gp_price_kb(context.user_data)); return
    if d=="use_perc":
        pending=context.user_data.get('pending_codes',[])
        if not pending: await q.edit_message_text("No pending"); return
        c=get_cfg(); calc=round(pending[0]['amount_val']*c['perc']/100,2) if pending[0]['amount_val']>0 else c['perc']
        prods=load_file("products.json"); created=[]
        for p in pending:
            pid=str(uuid.uuid4())[:6]; small=f"avl $ {p['amount'].replace('$','').strip()}"
            prod={"brand":p['brand'],"amount":small,"code":p['code'],"sell_price":calc,"sold":False,"category":p['category'],"g":context.user_data.get('g',True),"p":context.user_data.get('p',True),"reg":context.user_data.get('reg',True),"avl_small":small}
            prods[pid]=prod; created.append(prod)
        save_file("products.json", prods)
        context.user_data['wait']=None; context.user_data['pending_codes']=None
        await q.edit_message_text(f"✅ Added {len(created)} @ ${calc}", reply_markup=admin_main_kb())
        await post_to_channel(context, created); return
    if d=="custom_price_info":
        await q.edit_message_text("Type custom price $9.75"); context.user_data['wait']="add_price"; return
    if d.startswith("listings_"):
        cat=d.replace("listings_",""); prods=load_file("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold')] if cat=="All" else [(k,v) for k,v in prods.items() if not v.get('sold') and v.get('category')==cat]
        if not active: await q.edit_message_text(f"No stock {cat}"); return
        txt=premium_header(f"{cat} {len(active)}")+"\n"; kb=[]
        for pid,p in active[-15:][::-1]:
            first4=p['code'][:4]; avl=p.get('avl_small', f"avl {p['amount']}")
            txt+=f"💎 {first4}... {avl} ${p['sell_price']} G {'✅' if p.get('g',True) else '📴'} P {'✅' if p.get('p',True) else '📴'} REG {'✅' if p.get('reg',True) else '❌'}\n"
            kb.append([InlineKeyboardButton(f"💎 {first4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return
    if d=="show_filter":
        CATS=["All","Gift Card Mail","Free Fire","Call of Duty 880 CP","Amazon","Google Play","Other"]
        kb=[[InlineKeyboardButton(c, callback_data=f"listings_{c}")] for c in CATS]
        await q.edit_message_text(premium_header("FILTER"), reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p: await q.edit_message_text("Not found"); return
        first4=p['code'][:4]; avl=p.get('avl_small', f"avl {p['amount']}"); g="✅" if p.get('g',True) else "📴"; pp="✅" if p.get('p',True) else "📴"; r="✅" if p.get('reg',True) else "❌"
        await q.edit_message_text(premium_header("CARD DETAIL")+f"🎁 {first4}... {avl}\n💰 Price ${p['sell_price']}\nG {g} P {pp} REG {r}\n📦 {p.get('category')}\n🆔 {pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Buy ${p['sell_price']}", callback_data=f"buy_{pid}")]])); return
    if d.startswith("buy_"):
        pid=d.replace("buy_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get('sold'): await q.edit_message_text("❌ Sold!"); return
        first4=p['code'][:4]; avl=p.get('avl_small', f"avl {p['amount']}")
        await q.edit_message_text(premium_header("CONFIRM PURCHASE")+f"🎁 Item: {first4}... {avl}\n💰 Price: ${p['sell_price']}\n\nConfirm koro?", reply_markup=confirm_buy_kb(pid)); return
    if d.startswith("confirm_buy_"):
        pid=d.replace("confirm_buy_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get('sold'): await q.edit_messa
