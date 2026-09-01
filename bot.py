import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1q...")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "So1...")
STOCK_CHANNEL = os.getenv("STOCK_CHANNEL", "https://t.me/your_stock_channel")
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "@your_stock_channel")
SUPPORT_USER = os.getenv("SUPPORT_USER", "@your_support")
CHECKER_BOT = "@XprepaidCheckerBot"
VENDOR_PRICE = 15

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v74 FINAL FIXED"
@flask_app.route('/health')
def health(): return "OK"

def load_file(f, d=None):
    try:
        if os.path.exists(f):
            with open(f, "r") as x:
                return json.load(x)
    except:
        pass
    return d if d is not None else {}

def save_file(f, d):
    with open(f, "w") as x:
        json.dump(d, x, indent=2)

def get_user(uid):
    users = load_file("users.json")
    s = str(uid)
    if s not in users:
        users[s] = {"balance": 0, "purchases": [], "is_vendor": False, "sales": 0, "earn": 0}
        save_file("users.json", users)
    return users

def get_cfg():
    return load_file("config.json") or {"perc": 39, "comm": 5}

def get_amount(text):
    m = re.findall(r"\$([0-9]+\.?[0-9]*)", text)
    if m:
        try:
            return float(m[-1])
        except:
            pass
    return 0.0

def top_menu(admin=False):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚜️ Seller's Dashboard 🪝", callback_data="vendor_panel")],
        [InlineKeyboardButton("🔰 Listings", callback_data="list"), InlineKeyboardButton("🪪 Profile", callback_data="profile")],
    ])

def profile_menu(uid=0, bal=0):
    checker = CHECKER_BOT.replace('@','')
    deep_link = f"https://t.me/{checker}?start=check_{uid}_{bal}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏛️ Deposit Funds", callback_data="dep_funds"), InlineKeyboardButton("❄️ Balance Checker", url=deep_link)],
        [InlineKeyboardButton("🛒 Order History", callback_data="order_hist"), InlineKeyboardButton("🔄 Refresh", callback_data="profile")],
        [InlineKeyboardButton("🔙 Back", callback_data="main")]
    ])

def deposit_choice_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 LTC", callback_data="dep_ltc"), InlineKeyboardButton("💜 SOL", callback_data="dep_sol")],
        [InlineKeyboardButton("🔙 Back", callback_data="profile")]
    ])

def admin_kb():
    cfg = get_cfg()
    prods = load_file("products.json")
    stock = len([x for x in prods.values() if not x.get("sold")])
    sold = len([x for x in prods.values() if x.get("sold")])
    dep_pending = len([x for x in load_file("deposits.json").values() if x.get("status")=="pending"])
    order_pending = len([x for x in load_file("orders.json").values() if "pending" in x.get("status","")])
    perc = cfg.get('perc', 39)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock:{stock}", callback_data="noop"), InlineKeyboardButton(f"✅ Sold:{sold}", callback_data="noop")],
        [InlineKeyboardButton("📉 -5%", callback_data="perc_minus"), InlineKeyboardButton(f"📈 {perc}%", callback_data="set_perc"), InlineKeyboardButton("📈 +5%", callback_data="perc_plus")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add_gift"), InlineKeyboardButton("💵 Add Balance", callback_data="add_bal")],
        [InlineKeyboardButton(f"💳 Dep:{dep_pending}", callback_data="pending_dep"), InlineKeyboardButton(f"🛒 Orders:{order_pending}", callback_data="pending_orders")],
        [InlineKeyboardButton("👥 Users", callback_data="users_list"), InlineKeyboardButton("📋 Listings", callback_data="list")],
        [InlineKeyboardButton("🔙 Back", callback_data="main")]
    ])

def vendor_dash_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Giftcard", callback_data="add_gift")],
        [InlineKeyboardButton("📦 My Stock", callback_data="my_stock"), InlineKeyboardButton("📈 My Sales", callback_data="my_sales")],
        [InlineKeyboardButton("💰 Earnings", callback_data="my_earn"), InlineKeyboardButton("🔙 Back", callback_data="main")]
    ])

def vendor_buy_kb(bal):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👑 Buy Vendor {VENDOR_PRICE}$", callback_data="buy_vendor")],
        [InlineKeyboardButton("🏛️ Deposit Funds", callback_data="dep_funds")],
        [InlineKeyboardButton("🔙 Back", callback_data="main")]
    ])

def mark_kb(g, p, reg, price, orig):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🅶 {'✅ ON' if g else '❌ OFF'}", callback_data="mark_g"), InlineKeyboardButton(f"🅿️ {'✅ ON' if p else '❌ OFF'}", callback_data="mark_p"), InlineKeyboardButton(f"{'®️ REG' if reg else '🌐 UNREG'}", callback_data="mark_reg")],
        [InlineKeyboardButton("➖", callback_data="price_minus"), InlineKeyboardButton("📈 39% ✅ ON", callback_data="mark_39"), InlineKeyboardButton("➕", callback_data="price_plus")],
        [InlineKeyboardButton(f"💾 SAVE ${price}", callback_data="mark_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main")]
    ])

async def post_to_stock_channel(context, product, pid):
    try:
        code = product['code']
        masked = f"{code[:4]}...."
        price = product['price']
        avl = product.get('orig', '?')
        g = '✅' if product.get('g') else '❌'
        p = '✅' if product.get('p') else '❌'
        reg = 'REG ✅' if product.get('reg') else 'UNREG 🌐'
        txt = f"✨ NEW STOCK ✨\n\n💎 {masked} avl ${avl} ${price} G {g} P {p}\n{reg}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy Now", url=f"https://t.me/{context.bot.username}?start=buy_{pid}")]])
        await context.bot.send_message(chat_id=STOCK_CHANNEL_ID, text=txt, reply_markup=kb)
    except Exception as e:
        print(f"stock post fail {e}")

async def set_cmds(app):
    await app.bot.set_my_commands([
        BotCommand("start", "🚀 Launch"), BotCommand("latest", "📋 Latest"), BotCommand("stock", "📦 Stock"),
        BotCommand("deposit", "💰 Deposit"), BotCommand("support", "💬 Support"), BotCommand("profile", "👤 Profile"),
        BotCommand("admin", "👑 Admin"), BotCommand("vendor", "👑 Vendor"),
    ])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    cfg = get_cfg()
    bal = load_file("users.json").get(str(uid), {}).get("balance", 0)
    stock = len([x for x in load_file("products.json").values() if not x.get("sold")])
    await update.message.reply_text(f"🎁 PREPAIDS GIFT'S\n\n💰 Balance: ${bal}\n📦 Stock: {stock}\n📈 Rate: {cfg['perc']}%", reply_markup=top_menu(uid==ADMIN_ID))

async def latest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods = load_file("products.json")
    active = [(k, v) for k, v in prods.items() if not v.get("sold")]
    if not active:
        await update.message.reply_text("📋 No listings", reply_markup=top_menu(update.effective_user.id==ADMIN_ID))
        return
    kb = [[InlineKeyboardButton(f"{p['code'][:12]} ${p['price']}", callback_data=f"view_{pid}")] for pid, p in active[-10:][::-1]]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="main")])
    await update.message.reply_text(f"📋 Latest {len(active)}", reply_markup=InlineKeyboardMarkup(kb))

async def stock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📦 STOCK\n{STOCK_CHANNEL}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 Join", url=STOCK_CHANNEL)]]))

async def deposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏛️ Deposit Funds:", reply_markup=deposit_choice_kb())

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💬 Support {SUPPORT_USER}")

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid).get(str(uid), {})
    bal = u.get('balance', 0)
    await update.message.reply_text(f"🪪 PROFILE\nID: {uid}\n💰 Balance: ${bal}\n👑 Vendor: {'✅' if u.get('is_vendor') else '❌'}", reply_markup=profile_menu(uid, bal))

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("❌ Admin only")
        return
    cfg = get_cfg()
    await update.message.reply_text(f"👑 ADMIN {cfg['perc']}%", reply_markup=admin_kb())

async def vendor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    u = get_user(uid).get(str(uid), {})
    if u.get("is_vendor"):
        await update.message.reply_text("⚜️ SELLER'S DASHBOARD", reply_markup=vendor_dash_kb())
    else:
        await update.message.reply_text(f"Buy Vendor ${VENDOR_PRICE}", reply_markup=vendor_buy_kb(u.get('balance', 0)))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text or ""
    uid = update.effective_user.id
    if txt.startswith("/"):
        return
    wait = context.user_data.get("wait")
    if wait and wait.startswith("deposit_txid_"):
        coin = wait.replace("deposit_txid_", "")
        did = str(uuid.uuid4())[:6]
        deposits = load_file("deposits.json")
        deposits[did] = {"user_id": uid, "coin": coin, "txid": txt, "status": "pending"}
        save_file("deposits.json", deposits)
        bal = load_file("users.json").get(str(uid), {}).get("balance", 0)
        await update.message.reply_text(f"✅ Submitted {coin} {did}", reply_markup=profile_menu(uid, bal))
        try:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ {did}", callback_data=f"dep_approve_{did}"), InlineKeyboardButton(f"❌ {did}", callback_data=f"dep_reject_{did}")]])
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"💳 DEPOSIT {did} User:{uid} {coin} {txt}", reply_markup=kb)
        except:
            pass
        context.user_data["wait"] = None
        return
    if wait == "add_stock":
        amt = get_amount(txt)
        if amt == 0:
            await update.message.reply_text("❌ avl pai nai! Example: 4511... $25")
            return
        perc = get_cfg().get('perc', 39)
        calc = round(amt * perc / 100, 2)
        context.user_data.update({"pending_code": txt, "pending_amt": amt, "pending_price": calc, "mark_g": True, "mark_p": False, "mark_reg": True, "wait": "marking"})
        await update.message.reply_text(f"💳 {txt[:4]}.... avl ${amt}", reply_markup=mark_kb(True, False, True, calc, amt))
        return
    if wait == "set_price_custom":
        try:
            price = float(txt.replace("$", ""))
        except:
            await update.message.reply_text("Price dao e.g. 0.24")
            return
        context.user_data["pending_price"] = price
        context.user_data["wait"] = "marking"
        g = context.user_data.get("mark_g")
        p = context.user_data.get("mark_p")
        reg = context.user_data.get("mark_reg")
        avl = context.user_data.get("pending_amt")
        await update.message.reply_text(f"💳 {context.user_data.get('pending_code','')[:4]}.... avl ${avl}", reply_markup=mark_kb(g, p, reg, price, avl))
        return
    if wait == "set_perc_custom":
        try:
            perc = float(txt.replace("%", ""))
            cfg = get_cfg()
            cfg["perc"] = perc
            save_file("config.json", cfg)
            await update.message.reply_text(f"✅ Perc {perc}%", reply_markup=admin_kb())
        except:
            await update.message.reply_text("Number dao e.g. 39", reply_markup=admin_kb())
        context.user_data["wait"] = None
        return
    if wait == "add_bal":
        try:
            parts = txt.split()
            uid_t = parts[0]
            amt = float(parts[1])
            users = load_file("users.json")
            if uid_t not in users:
                users[uid_t] = {"balance": 0, "purchases": [], "is_vendor": False, "sales": 0, "earn": 0}
            users[uid_t]["balance"] = users[uid_t].get("balance", 0) + amt
            save_file("users.json", users)
            await update.message.reply_text(f"✅ Added ${amt} to {uid_t}", reply_markup=admin_kb())
            try:
                await context.bot.send_message(chat_id=int(uid_t), text=f"💰 Added ${amt}!")
            except:
                pass
        except:
            await update.message.reply_text("Format: USERID AMOUNT", reply_markup=admin_kb())
        context.user_data["wait"] = None
        return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    users = get_user(uid)
    u = users.get(str(uid), {})
    bal = u.get("balance", 0)
    cfg = get_cfg()

    if d == "main":
        stock = len([x for x in load_file("products.json").values() if not x.get("sold")])
        await q.edit_message_text(f"🎁 PREPAIDS GIFT'S\n💰 Bal: ${bal}\n📦 Stock: {stock}\n📈 {cfg['perc']}%", reply_markup=top_menu(uid==ADMIN_ID))
        return
    if d == "profile":
        await q.edit_message_text(f"🪪 PROFILE\nID: {uid}\n💰 Balance: ${bal}\n👑 Vendor: {'✅' if u.get('is_vendor') else '❌'}", reply_markup=profile_menu(uid, bal))
        return
    if d == "dep_funds":
        await q.edit_message_text("🏛️ Deposit Funds", reply_markup=deposit_choice_kb())
        return
    if d == "order_hist":
        pur = u.get("purchases", [])[-10:]
        msg = f"🛒 Order History {len(pur)}\n"
        for p in pur[::-1]:
            msg += f"• {p.get('code','')[:15]} ${p.get('price')}\n"
        if not pur:
            msg = "No orders"
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="profile")]]))
        return
    if d == "dep_ltc":
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={LTC_ADDRESS}"
        txt = f"💎 LTC Deposit\nAddress:\n`{LTC_ADDRESS}`\nMin $5"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📤 Submit TXID", callback_data="submit_ltc")], [InlineKeyboardButton("🔙 Back", callback_data="dep_funds")]])
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
        try:
            await context.bot.send_photo(chat_id=uid, photo=qr)
        except:
            pass
        return
    if d == "dep_sol":
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={SOL_ADDRESS}"
        txt = f"💜 SOL Deposit\nAddress:\n`{SOL_ADDRESS}`\nMin $5"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📤 Submit TXID", callback_data="submit_sol")], [InlineKeyboardButton("🔙 Back", callback_data="dep_funds")]])
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
        try:
            await context.bot.send_photo(chat_id=uid, photo=qr)
        except:
            pass
        return
    if d == "submit_ltc":
        context.user_data["wait"] = "deposit_txid_LTC"
        await q.edit_message_text("Paste LTC TXID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="dep_funds")]]))
        return
    if d == "submit_sol":
        context.user_data["wait"] = "deposit_txid_SOL"
        await q.edit_message_text("Paste SOL TXID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="dep_funds")]]))
        return
    if d == "list":
        prods = load_file("products.json")
        active = [(k, v) for k, v in prods.items() if not v.get("sold")]
        if not active:
            await q.edit_message_text("📋 No listings", reply_markup=top_menu(uid==ADMIN_ID))
            return
        kb = [[InlineKeyboardButton(f"{p['code'][:12]} ${p['price']}", callback_data=f"view_{pid}")] for pid, p in active[-15:][::-1]]
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="main")])
        await q.edit_message_text(f"🔰 Listings {len(active)}", reply_markup=InlineKeyboardMarkup(kb))
        return
    if d == "admin":
        if uid!= ADMIN_ID:
            return
        await q.edit_message_text(f"👑 ADMIN {cfg['perc']}%", reply_markup=admin_kb())
        return
    if d == "perc_plus":
        if uid!= ADMIN_ID:
            return
        cfg["perc"] = min(100, cfg.get('perc', 39) + 5)
        save_file("config.json", cfg)
        await q.edit_message_text(f"👑 ADMIN {cfg['perc']}%", reply_markup=admin_kb())
        return
    if d == "perc_minus":
        if uid!= ADMIN_ID:
            return
        cfg["perc"] = max(5, cfg.get('perc', 39) - 5)
        save_file("config.json", cfg)
        await q.edit_message_text(f"👑 ADMIN {cfg['perc']}%", reply_markup=admin_kb())
        return
    if d == "vendor_panel":
        if u.get("is_vendor"):
            prods = load_file("products.json")
            my_stock = len([p for p in prods.values() if p.get("owner") == uid and not p.get("sold")])
            my_sold = len([p for p in prods.values() if p.get("owner") == uid and p.get("sold")])
            await q.edit_message_text(f"⚜️ SELLER'S DASHBOARD 🪝\n📦 Stock: {my_stock}\n✅ Sold: {my_sold}\n💰 Earn: ${u.get('earn',0)}\n💳 Bal: ${bal}", reply_markup=vendor_dash_kb())
        else:
            await q.edit_message_text(f"⚜️ SELLER'S DASHBOARD\nBuy Vendor ${VENDOR_PRICE} Bal ${bal}", reply_markup=vendor_buy_kb(bal))
        return
    if d == "buy_vendor":
        if u.get("is_vendor"):
            await q.edit_message_text("Already vendor!", reply_markup=vendor_dash_kb())
            return
        if bal < VENDOR_PRICE:
            await q.edit_message_text(f"❌ Need ${VENDOR_PRICE} Bal ${bal}", reply_markup=vendor_buy_kb(bal))
            return
        users[str(uid)]["balance"] = bal - VENDOR_PRICE
        users[str(uid)]["is_vendor"] = True
        save_file("users.json", users)
        await q.edit_message_text("✅ BOUGHT!", reply_markup=vendor_dash_kb())
        return
    if d == "my_stock":
        prods = load_file("products.json")
        my = [(k, v) for k, v in prods.items() if v.get("owner") == uid and not v.get("sold")]
        msg = f"📦 My Stock {len(my)}\n"
        kb = []
        for pid, p in my[-10:]:
            msg += f"{p['code'][:12]} ${p['price']}\n"
            kb.append([InlineKeyboardButton(f"🗑️ {p['code'][:6]}", callback_data=f"del_{pid}")])
        if not my:
            msg = "No stock"
        kb.append([InlineKeyboardButton("➕ Add", callback_data="add_gift"), InlineKeyboardButton("🔙 Back", callback_data="vendor_panel")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("del_"):
        pid = d.replace("del_", "")
        prods = load_file("products.json")
        if pid in prods and prods[pid].get("owner") == uid:
            del prods[pid]
            save_file("products.json", prods)
            await q.edit_message_text(f"Deleted {pid}", reply_markup=vendor_dash_kb())
        return
    if d == "my_sales":
        prods = load_file("products.json")
        sold = [(k, v) for k, v in prods.items() if v.get("owner") == uid and v.get("sold")]
        msg = f"📈 Sales {len(sold)}\n"
        for pid, p in sold[-10:]:
            msg += f"{p['code'][:10]} ${p['price']}\n"
        if not sold:
            msg = "No sales"
        await q.edit_message_text(msg, reply_markup=vendor_dash_kb())
        return
    if d == "my_earn":
        await q.edit_message_text(f"💰 Earn ${u.get('earn',0)}", reply_markup=vendor_dash_kb())
        return
    if d == "add_gift":
        context.user_data["wait"] = "add_stock"
        await q.edit_message_text("📝 SEND: `4511... $25` last $ = avl", pars
