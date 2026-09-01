import os, json, uuid, threading, re, random, time, html
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6699688350"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "")
LTC_ADDRESS = os.getenv("LTC_ADDRESS", "ltc1q_test_123456")
SOL_ADDRESS = os.getenv("SOL_ADDRESS", "SoL_test_123456")
BINANCE_ID = os.getenv("BINANCE_ID", "123456789")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "MEGA 2100 LINES BOT - ALL FEATURES LIVE - CONFIRM/CANCEL + G/P/REG + 4 DIGIT CHANNEL + BOTTOM BUTTONS + SHORTCUT"
@flask_app.route('/health')
def health(): return "OK"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

# ===================== FILE HELPERS =====================
def load_file(f, d=None):
    if d is None: d = {}
    if not os.path.exists(f): return d
    try:
        with open(f, 'r', encoding='utf-8') as file: return json.load(file)
    except: return d

def save_file(f, d):
    with open(f, 'w', encoding='utf-8') as file: json.dump(d, file, indent=2)

def get_cfg():
    default = {
        "perc": 39, "perc_enabled": True, "comm": 5, "auto_update": True,
        "version": "21.0 MEGA 2100 LINES", "vendor_enabled": True, "relist_enabled": True,
        "vendor_price": 20, "relist_price": 15, "maintenance": False,
        "daily_bonus": 0.5, "refer_perc": 5, "min_withdraw": 10,
        "auto_delete": True, "rating_enabled": True, "dispute_enabled": True
    }
    cfg = load_file("config.json", default)
    for k, v in default.items():
        if k not in cfg: cfg[k] = v
    return cfg

def get_user(uid_s):
    users = load_file("users.json")
    if uid_s not in users:
        users[uid_s] = {
            "balance": 0, "vendor_access": False, "relist_access": False,
            "purchases": [], "refer": 0, "refer_earn": 0, "wishlist": [],
            "cart": [], "daily_claimed": "", "rating": 0, "total_spent": 0,
            "withdraw_pending": 0, "lang": "en", "notify": True, "banned": False
        }
        save_file("users.json", users)
    return users

def get_products():
    return load_file("products.json")

def get_orders():
    return load_file("orders.json")

def get_vendor_requests():
    return load_file("vendor_requests.json", {})

def get_coupons():
    return load_file("coupons.json", {})

def get_redeems():
    return load_file("redeems.json", {})

def get_withdraws():
    return load_file("withdraws.json", {})

def get_ratings():
    return load_file("ratings.json", {})

def get_disputes():
    return load_file("disputes.json", {})

def get_logs():
    return load_file("logs.json", [])

def add_log(action, uid, details=""):
    logs = get_logs()
    logs.append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "action": action, "uid": uid, "details": details})
    if len(logs) > 500: logs = logs[-500:]
    save_file("logs.json", logs)

def premium_header(t): return f"╔═══════════════╗\n 💎 {t} 💎\n╚═══════════════╝\n"

# ===================== CATEGORIES =====================
CATEGORIES = [
    "Gift Card Mail", "Free Fire", "Call of Duty 880 CP", "Call of Duty Gift Card",
    "Call of Duty Points", "PUBG", "PUBG UC", "Amazon", "Google Play", "iTunes",
    "Steam", "PlayStation", "Xbox", "Netflix", "Spotify", "Other"
]

# ===================== KEYBOARDS =====================
def main_reply_kb(is_admin=False):
    kb = [
        [KeyboardButton("💳 My Balance"), KeyboardButton("👤 My Profile")],
        [KeyboardButton("📋 Browse Cards"), KeyboardButton("🔍 Check Card")],
        [KeyboardButton("💰 Deposit"), KeyboardButton("💸 Withdraw")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("🔑 Redeem Code")],
        [KeyboardButton("⚙️ Filter"), KeyboardButton("🆘 Support")],
        [KeyboardButton("🎁 Daily Bonus"), KeyboardButton("🛒 My Cart")],
    ]
    if is_admin:
        kb.append([KeyboardButton("👑 Admin Panel"), KeyboardButton("✏️ Edit Panel")])
        kb.append([KeyboardButton("➕ Add Stock"), KeyboardButton("📊 Analytics")])
        kb.append([KeyboardButton("📢 Broadcast"), KeyboardButton("💾 Backup")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, is_persistent=True)

def admin_main_kb():
    p = load_file("products.json"); s = len([x for x in p.values() if not x.get('sold')]); c = get_cfg()
    vreq = len([x for x in load_file("vendor_requests.json", {}).values() if x.get('status') == 'pending'])
    pending = len([x for x in load_file("orders.json", {}).values() if x.get('status') == 'pending'])
    wpending = len([x for x in load_file("withdraws.json", {}).values() if x.get('status') == 'pending'])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock: {s}", callback_data="stock"), InlineKeyboardButton(f"⏳ Orders ({pending})", callback_data="orders")],
        [InlineKeyboardButton(f"🧑‍💼 Vendor Req ({vreq})", callback_data="vreq"), InlineKeyboardButton(f"💸 Withdraw ({wpending})", callback_data="wpending")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add"), InlineKeyboardButton("💲 Set %", callback_data="perc")],
        [InlineKeyboardButton(f"📊 {c['perc']}% {'ON ✅' if c.get('perc_enabled') else 'OFF ❌'}", callback_data="toggle_perc_global")],
        [InlineKeyboardButton("✏️ Easy Edit", callback_data="edit_list"), InlineKeyboardButton("🔍 Filter Edit", callback_data="filter_admin")],
        [InlineKeyboardButton("💵 Add Balance", callback_data="addbal"), InlineKeyboardButton("🎁 Add Redeem", callback_data="add_redeem")],
        [InlineKeyboardButton("👥 All Sellers", callback_data="sellers"), InlineKeyboardButton("📜 Buyer History", callback_data="bhist")],
        [InlineKeyboardButton("📊 Sales Analytics", callback_data="analytics"), InlineKeyboardButton("💾 Backup/Restore", callback_data="backup")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"), InlineKeyboardButton("⚙️ Maintenance", callback_data="maintenance")],
        [InlineKeyboardButton("📋 Logs", callback_data="logs"), InlineKeyboardButton("⭐ Ratings", callback_data="ratings")],
        [InlineKeyboardButton("⚠️ Disputes", callback_data="disputes"), InlineKeyboardButton("🎟️ Coupons", callback_data="coupons")],
    ])

def build_gp_price_kb(ctx_data):
    c = get_cfg(); perc = c['perc']; enabled = c['perc_enabled']
    g = ctx_data.get('g', True); p = ctx_data.get('p', True); reg = ctx_data.get('reg', True)
    g_icon = "✅" if g else "📴"
    p_icon = "✅" if p else "📴"
    reg_icon = "✅" if reg else "❌"
    perc_icon = "ON ✅" if enabled else "OFF ❌"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {g_icon}", callback_data="toggle_g"), InlineKeyboardButton(f"P {p_icon}", callback_data="toggle_p"), InlineKeyboardButton(f"REGISTERED {reg_icon}", callback_data="toggle_reg")],
        [InlineKeyboardButton(f"📊 {perc}% ({perc_icon})", callback_data="toggle_perc_add")],
        [InlineKeyboardButton(f"✅ Use {perc}% Price", callback_data="use_perc"), InlineKeyboardButton("💲 Custom $9.75", callback_data="custom_price_info")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")],
    ])

def confirm_buy_kb(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_buy_{pid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_buy_{pid}")],
        [InlineKeyboardButton("🛒 Add to Cart", callback_data=f"addcart_{pid}"), InlineKeyboardButton("💖 Wishlist", callback_data=f"wish_{pid}")],
    ])

def after_purchase_kb(oid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Refund Request", callback_data=f"refund_{oid}"), InlineKeyboardButton("📜 Transactions", callback_data="hist")],
        [InlineKeyboardButton("🌀 ReCheck Card", callback_data=f"recheck_{oid}"), InlineKeyboardButton("🔄 ReList Card", callback_data=f"relist_one_{oid}")],
        [InlineKeyboardButton("⭐ Rate", callback_data=f"rate_{oid}"), InlineKeyboardButton("⚠️ Dispute", callback_data=f"dispute_{oid}")],
        [InlineKeyboardButton("🛒 Buy More", callback_data="listings_All")],
    ])

def filter_kb():
    kb = []
    for i in range(0, len(CATEGORIES), 2):
        row = [InlineKeyboardButton(CATEGORIES[i], callback_data=f"listings_{CATEGORIES[i]}")]
        if i + 1 < len(CATEGORIES): row.append(InlineKeyboardButton(CATEGORIES[i+1], callback_data=f"listings_{CATEGORIES[i+1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("📋 All", callback_data="listings_All")])
    return InlineKeyboardMarkup(kb)

def deposit_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("◎ SOL", callback_data="dep_sol")],
        [InlineKeyboardButton("💳 Binance Pay", callback_data="dep_binance")],
    ])

# ===================== CHANNEL POST =====================
async def post_to_channel(context, prods):
    if not STOCK_CHANNEL_ID: return
    try:
        msg = premium_header("NEW STOCK AVAILABLE") + "\n"
        for p in prods:
            first4 = p['code'][:4] if len(p['code']) >= 4 else p['code'][:3]
            avl = p.get('avl_small', f"avl $ {p['amount'].replace('$','').strip()}")
            g_icon = "✅" if p.get('g', True) else "📴"
            p_icon = "✅" if p.get('p', True) else "📴"
            reg_icon = "✅" if p.get('reg', True) else "❌"
            msg += f"💎 `{first4}...` {avl} | Price ${p['sell_price']} | G {g_icon} P {p_icon} REG {reg_icon} | {p['category']}\n"
        msg += f"\n📦 Total: {len(prods)} new\n🛒 Buy: /listings\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        chat_id = int(STOCK_CHANNEL_ID) if not STOCK_CHANNEL_ID.startswith('@') else STOCK_CHANNEL_ID
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Buy Now", callback_data="listings_All")]])
        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=kb, parse_mode='Markdown')
    except Exception as e:
        print(f"Channel post failed: {e}")

# ===================== BOT COMMANDS MENU =====================
async def set_bot_commands(app):
    commands = [
        BotCommand("start", "🚀 Launch bot"),
        BotCommand("profile", "👤 View profile"),
        BotCommand("balance", "💳 View balance"),
        BotCommand("deposit", "💰 Deposit"),
        BotCommand("listings", "📋 Browse Cards"),
        BotCommand("filter", "⚙️ Filter"),
        BotCommand("support", "🆘 Support"),
        BotCommand("refer", "👥 Refer & Earn"),
        BotCommand("check", "🔍 Check Card"),
        BotCommand("withdraw", "💸 Withdraw"),
        BotCommand("redeem", "🔑 Redeem Code"),
        BotCommand("cart", "🛒 My Cart"),
        BotCommand("wishlist", "💖 Wishlist"),
        BotCommand("daily", "🎁 Daily Bonus"),
    ]
    try: await app.bot.set_my_commands(commands); print("✅ Shortcut Menu Set!")
    except Exception as e: print(e)

# ===================== COMMAND HANDLERS =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; uid_s = str(uid)
    users = get_user(uid_s)
    cfg = get_cfg()
    if cfg.get('maintenance') and uid!= ADMIN_ID:
        await update.message.reply_text("🔧 Bot under maintenance! Try later."); return
    # Referral
    if context.args and len(context.args) > 0:
        ref_id = context.args[0]
        if ref_id!= uid_s and ref_id in users:
            if users[uid_s].get('referred') is None:
                users[uid_s]['referred'] = ref_id
                users[ref_id]['refer'] = users[ref_id].get('refer', 0) + 1
                save_file("users.json", users)
                add_log("referral", uid_s, f"referred by {ref_id}")
    await update.message.reply_text(f"Welcome {update.effective_user.first_name}!\n\n🎉 prepaids gift's bot\n💎 16 Categories | Vendor ${cfg['vendor_price']} | Relist ${cfg['relist_price']}\n\n👇 Menu chaple shortcut + niche buttons!", reply_markup=main_reply_kb(uid == ADMIN_ID))
    if uid == ADMIN_ID:
        await update.message.reply_text(premium_header("ADMIN PANEL") + f"Version: {cfg['version']}\nStock: {len([x for x in load_file('products.json').values() if not x.get('sold')])}", reply_markup=admin_main_kb())

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; uid_s = str(uid); users = get_user(uid_s); u = users[uid_s]; pur = u.get('purchases', []); cfg = get_cfg()
    v = "✅ Enabled" if u.get('vendor_access') else f"❌ Disabled - ${cfg['vendor_price']}"
    r = "✅ Enabled" if u.get('relist_access') else f"❌ Disabled - ${cfg['relist_price']}"
    txt = premium_header("MY PROFILE DASHBOARD") + f"🆔 Username: @{update.effective_user.username or 'N/A'}\n🆔 User ID: {uid}\n👤 Name: {update.effective_user.first_name}\n💰 Balance: ${u.get('balance',0)}\n💸 Pending Withdraw: ${u.get('withdraw_pending',0)}\n🛒 Total Purchase: {len(pur)}\n💵 Total Spent: ${u.get('total_spent',0)}\n👥 Refer: {u.get('refer',0)} Earn: ${u.get('refer_earn',0)}\n\n🏪 Vendor: {v}\n🔄 Relist: {r}\n\n📜 Last 5:\n"
    for o in pur[-5:][::-1]: txt += f"• {o.get('id')} {o.get('brand')} {o.get('avl_small','')} ${o.get('sell_price')} {o.get('status')}\n"
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🏪 Buy Vendor ${cfg['vendor_price']}", callback_data="buy_vendor"), InlineKeyboardButton(f"🔄 Buy Relist ${cfg['relist_price']}", callback_data="buy_relist")]]))

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; users = get_user(str(uid))
    await update.message.reply_text(f"💳 Balance: ${users[str(uid)].get('balance',0)}\n💸 Pending Withdraw: ${users[str(uid)].get('withdraw_pending',0)}\n💵 Total Spent: ${users[str(uid)].get('total_spent',0)}", reply_markup=main_reply_kb(uid == ADMIN_ID))

async def deposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium_header("DEPOSIT") + f"🪙 LTC Address:\n`{LTC_ADDRESS}`\n\n◎ SOL Address:\n`{SOL_ADDRESS}`\n\n💳 Binance ID: `{BINANCE_ID}`\n\nMin $5 - TXID send admin", reply_markup=deposit_kb(), parse_mode='Markdown')

async def listings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prods = load_file("products.json"); active = [(k, v) for k, v in prods.items() if not v.get('sold')]
    if not active: await update.message.reply_text("❌ No stock!"); return
    # Sorting: newest first
    msg = premium_header(f"Browse Cards ({len(active)})") + "\n"; kb = []
    for pid, p in active[-15:][::-1]:
        first4 = p['code'][:4]; avl = p.get('avl_small', f"avl {p['amount']}"); g = "✅" if p.get('g', True) else "📴"; p_ = "✅" if p.get('p', True) else "📴"; r = "✅" if p.get('reg', True) else "❌"
        msg += f"💎 {first4}... {avl} ${p['sell_price']} G {g} P {p_} REG {r} [{p.get('category')}]\n"
        kb.append([InlineKeyboardButton(f"💎 {first4}... {avl} ${p['sell_price']}", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("⚙️ Filter", callback_data="filter"), InlineKeyboardButton("🔍 Search", callback_data="search")])
    kb.append([InlineKeyboardButton("⬅️ Prev", callback_data="page_prev"), InlineKeyboardButton("Next ➡️", callback_data="page_next")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(premium_header("FILTER 16 CATEGORIES"), reply_markup=filter_kb())

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("🆘 Support: @toma | Channel: @yourchannel\n📋 Logs: /logs\n⭐ Rate: /rate\n⚠️ Dispute: /dispute")
async def refer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; users = get_user(str(uid))
    await update.message.reply_text(f"👥 Refer & Earn\nLink: https://t.me/{context.bot.username}?start={uid}\nEarn {get_cfg()['refer_perc']}%\nTotal Refer: {users[str(uid)].get('refer',0)} Earn: ${users[str(uid)].get('refer_earn',0)}")
async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("🔍 Check Card\nSend Order ID: /check ORDERID or use ReCheck button")
async def withdraw_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; users = get_user(str(uid))
    await update.message.reply_text(f"💸 Withdraw\nBalance: ${users[str(uid)].get('balance',0)}\nMin ${get_cfg()['min_withdraw']}\nSend amount + address:\nEx: 20 LTC_ADDRESS\nAdmin approval needed!", reply_markup=main_reply_kb(uid == ADMIN_ID))
async def redeem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wait'] = "redeem"
    await update.message.reply_text("🔑 Redeem Code\nSend your redeem code:", reply_markup=main_reply_kb(update.effective_user.id == ADMIN_ID))
async def cart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; users = get_user(str(uid)); cart = users[str(uid)].get('cart', [])
    if not cart: await update.message.reply_text("🛒 Cart empty!"); return
    msg = premium_header(f"My Cart ({len(cart)})") + "\n"
    total = 0
    for pid in cart:
        p = load_file("products.json").get(pid)
        if p: msg += f"• {p['code'][:4]}... {p.get('avl_small','')} ${p['sell_price']}\n"; total += p['sell_price']
    msg += f"\nTotal: ${total}\n"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Checkout ${total}", callback_data="checkout"), InlineKeyboardButton("❌ Clear Cart", callback_data="clear_cart")]]))
async def wishlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; users = get_user(str(uid)); wish = users[str(uid)].get('wishlist', [])
    if not wish: await update.message.reply_text("💖 Wishlist empty!"); return
    msg = premium_header(f"Wishlist ({len(wish)})") + "\n" + "\n".join([f"• {pid}" for pid in wish[:10]])
    await update.message.reply_text(msg)
async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; uid_s = str(uid); users = get_user(uid_s); cfg = get_cfg()
    today = datetime.now().strftime("%Y-%m-%d")
    if users[uid_s].get('daily_claimed') == today:
        await update.message.reply_text("🎁 Already claimed today! Come tomorrow."); return
    bonus = cfg.get('daily_bonus', 0.5)
    users[uid_s]['balance'] = users[uid_s].get('balance', 0) + bonus
    users[uid_s]['daily_claimed'] = today
    save_file("users.json", users)
    await update.message.reply_text(f"🎁 Daily Bonus claimed! +${bonus} added! New balance: ${users[uid_s]['balance']}")
    add_log("daily_bonus", uid_s, f"+${bonus}")

# ===================== MESSAGE HANDLER =====================
async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip(); wait = context.user_data.get('wait'); uid = update.effective_user.id; uid_s = str(uid)
    cfg = get_cfg()

    # Maintenance
    if cfg.get('maintenance') and uid!= ADMIN_ID:
        await update.message.reply_text("🔧 Maintenance mode! Try later."); return

    # Bottom buttons
    if "My Balance" in txt: await balance_cmd(update, context); return
    elif "My Profile" in txt: await profile_cmd(update, context); return
    elif "Browse Cards" in txt: await listings_cmd(update, context); return
    elif "Check Card" in txt: await check_cmd(update, context); return
    elif "Deposit" in txt: await deposit_cmd(update, context); return
    elif "Withdraw" in txt:
