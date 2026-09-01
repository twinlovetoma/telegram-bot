import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
VENDOR_PRICE = 15

flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "v54 LIVE"
@flask_app.route('/health')
def health():
    return "OK"

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
        users[s] = {"balance": 0, "purchases": [], "is_vendor": False, "vendor_sales": 0, "vendor_earn": 0}
        save_file("users.json", users)
    return users

def get_cfg():
    return load_file("config.json") or {"perc": 39, "comm": 5}

def top_menu(admin=False):
    kb = [
        [InlineKeyboardButton("Listings", callback_data="top_list"), InlineKeyboardButton("Filter", callback_data="top_filter")],
        [InlineKeyboardButton("Deposit", callback_data="top_dep"), InlineKeyboardButton("Profile", callback_data="top_profile")],
    ]
    if admin:
        kb.append([InlineKeyboardButton("Admin Panel", callback_data="top_admin")])
    return InlineKeyboardMarkup(kb)

def admin_kb():
    cfg = get_cfg()
    stock = len([x for x in load_file("products.json").values() if not x.get("sold")])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Stock:{stock}", callback_data="stock_info"), InlineKeyboardButton(f"Set {cfg['perc']}%", callback_data="set_perc")],
        [InlineKeyboardButton("Add Stock", callback_data="add_stock"), InlineKeyboardButton("Add Balance", callback_data="add_bal")],
        [InlineKeyboardButton("Pending COD", callback_data="pending_cod")],
        [InlineKeyboardButton("Back", callback_data="main_menu")]
    ])

def vendor_dash_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Giftcard", callback_data="add_giftcard"), InlineKeyboardButton("Add COD", callback_data="add_cod")],
        [InlineKeyboardButton("My Stock", callback_data="my_vendor_stock"), InlineKeyboardButton("My Sales", callback_data="vendor_sales")],
        [InlineKeyboardButton("Earnings", callback_data="vendor_earn"), InlineKeyboardButton("Back", callback_data="main_menu")]
    ])

def vendor_buy_kb(bal):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Buy Vendor {VENDOR_PRICE}$", callback_data="buy_vendor")],
        [InlineKeyboardButton(f"Deposit Bal {bal}$", callback_data="top_dep")],
        [InlineKeyboardButton("Back", callback_data="main_menu")]
    ])

def welcome():
    cfg = get_cfg()
    return f"WELCOME PERC {cfg['perc']}%"

def mark_kb(g, p, reg, price, amt, cat="Giftcard"):
    g_txt = "G ON" if g else "G OFF"
    p_txt = "P ON" if p else "P OFF"
    r_txt = "REG" if reg else "UNREG"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(g_txt, callback_data="mark_g"), InlineKeyboardButton(p_txt, callback_data="mark_p"), InlineKeyboardButton(r_txt, callback_data="mark_reg")],
        [InlineKeyboardButton("-1", callback_data="price_minus"), InlineKeyboardButton(f"{price}$", callback_data="price_custom"), InlineKeyboardButton("+1", callback_data="price_plus")],
        [InlineKeyboardButton(cat, callback_data="noop"), InlineKeyboardButton(f"Save {price}$", callback_data="mark_save")],
        [InlineKeyboardButton("Cancel", callback_data="vendor_panel")]
    ])

def get_amount(text):
    nums = re.findall(r"[0-9]+", text)
    if nums:
        try:
            return float(nums[-1])
        except:
            return 25.0
    return 25.0

async def set_cmds(app):
    cmds = [
        BotCommand("start", "Launch bot"),
        BotCommand("listings", "Browse"),
        BotCommand("filter", "Filter"),
        BotCommand("profile", "View profile"),
        BotCommand("balance", "View balance"),
        BotCommand("deposit", "Deposit"),
        BotCommand("vendor", "Vendor Full"),
        BotCommand("admin", "Admin Panel"),
    ]
    try:
        await app.bot.set_my_commands(cmds)
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    await update.message.reply_text(welcome(), reply_markup=top_menu(update.effective_user.id == ADMIN_ID))

async def listings_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    prods = load_file("products.json")
    active = [(k, v) for k, v in prods.items() if not v.get("sold")]
    if not active:
        await update.message.reply_text("NO STOCK", reply_markup=top_menu(update.effective_user.id == ADMIN_ID))
        return
    msg = f"LISTINGS {len(active)}\n"
    kb = []
    for pid, p in active[-10:][::-1]:
        msg += f"{p['code'][:10]} {p['price']}$\n"
        kb.append([InlineKeyboardButton(f"{p['code'][:6]} {p['price']}$", callback_data=f"view_{pid}")])
    kb.append([InlineKeyboardButton("Filter", callback_data="top_filter")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

async def filter_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("All", callback_data="filter_All"), InlineKeyboardButton("Giftcard", callback_data="filter_Giftcard")],
        [InlineKeyboardButton("COD 880 CP", callback_data="filter_COD")],
        [InlineKeyboardButton("Back", callback_data="main_menu")]
    ])
    await update.message.reply_text("FILTER", reply_markup=kb)

async def profile_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users = get_user(uid)
    u = users.get(str(uid), {})
    bal = u.get("balance", 0)
    vendor = "Active" if u.get("is_vendor") else "Not Active"
    text = f"PROFILE ID {uid} Bal {bal}$ Vendor {vendor}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Vendor Panel", callback_data="vendor_panel")], [InlineKeyboardButton("Back", callback_data="main_menu")]])
    await update.message.reply_text(text, reply_markup=kb)

async def balance_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    u = load_file("users.json").get(str(update.effective_user.id), {})
    await update.message.reply_text(f"BALANCE {u.get('balance', 0)}$", reply_markup=top_menu(update.effective_user.id == ADMIN_ID))

async def deposit_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("DEPOSIT LTC SOL", reply_markup=top_menu(update.effective_user.id == ADMIN_ID))

async def vendor_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users = get_user(uid)
    u = users.get(str(uid), {})
    bal = u.get("balance", 0)
    is_vendor = u.get("is_vendor", False)
    if is_vendor:
        prods = load_file("products.json")
        my_stock = len([p for p in prods.values() if p.get("owner") == uid and not p.get("sold")])
        my_sold = len([p for p in prods.values() if p.get("owner") == uid and p.get("sold")])
        earn = u.get("vendor_earn", 0)
        text = f"VENDOR FULL Stock {my_stock} Sold {my_sold} Earn {earn}$ Bal {bal}$"
        await update.message.reply_text(text, reply_markup=vendor_dash_kb())
    else:
        text = f"VENDOR BUY Price {VENDOR_PRICE}$ Bal {bal}$"
        await update.message.reply_text(text, reply_markup=vendor_buy_kb(bal))

async def admin_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return
    await update.message.reply_text("ADMIN PANEL", reply_markup=admin_kb())

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text or ""
    uid = update.effective_user.id
    if txt.startswith("/"):
        return
    wait = context.user_data.get("wait")

    if wait and wait.startswith("activate_"):
        oid = wait.replace("activate_", "")
        orders = load_file("orders.json")
        if oid in orders:
            orders[oid]["activation"] = txt
            orders[oid]["status"] = "pending_activation"
            save_file("orders.json", orders)
            await update.message.reply_text(f"Your order was processing we notify you after complete Order {oid}", reply_markup=top_menu(uid == ADMIN_ID))
            try:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("Approve", callback_data=f"approve_cod_{oid}"), InlineKeyboardButton("Reject", callback_data=f"reject_cod_{oid}")]])
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"COD {oid} Buyer {uid} {txt}", reply_markup=kb)
            except:
                pass
        context.user_data["wait"] = None
        return

    if wait == "add_cod_title":
        context.user_data["pending_code"] = txt
        context.user_data["pending_amt"] = 10
        context.user_data["pending_price"] = 10
        context.user_data["pending_codes"] = [txt]
        context.user_data["upload_type"] = "COD"
        context.user_data["mark_g"] = False
        context.user_data["mark_p"] = False
        context.user_data["mark_reg"] = False
        context.user_data["wait"] = "marking"
        await update.message.reply_text(f"COD {txt}", reply_markup=mark_kb(False, False, False, 10, 10, "COD"))
        return

    if wait == "add_stock":
        amt = get_amount(txt)
        cfg = get_cfg()
        calc = round(amt * cfg["perc"] / 100, 2)
        context.user_data["pending_code"] = txt
        context.user_data["pending_amt"] = amt
        context.user_data["pending_price"] = calc
        context.user_data["pending_codes"] = [txt]
        context.user_data["upload_type"] = "Giftcard"
        context.user_data["mark_g"] = False
        context.user_data["mark_p"] = False
        context.user_data["mark_reg"] = False
        context.user_data["wait"] = "marking"
        await update.message.reply_text(f"Giftcard {txt[:20]} {calc}$", reply_markup=mark_kb(False, False, False, calc, amt, "Giftcard"))
        return

    if wait == "set_price":
        try:
            price = float(txt.replace("$", ""))
        except:
            await update.message.reply_text("Send price e.g. 8.5")
            return
        context.user_data["pending_price"] = price
        g = context.user_data.get("mark_g", False)
        p = context.user_data.get("mark_p", False)
        reg = context.user_data.get("mark_reg", False)
        amt = context.user_data["pending_amt"]
        cat = context.user_data.get("upload_type", "Giftcard")
        context.user_data["wait"] = "marking"
        await update.message.reply_text(f"Price {price}$", reply_markup=mark_kb(g, p, reg, price, amt, cat))
        return

    if wait == "add_bal":
        try:
            parts = txt.split()
            uid_t = parts[0]
            amt = float(parts[1])
            users = load_file("users.json")
            users[uid_t]["balance"] = users[uid_t].get("balance", 0) + amt
            save_file("users.json", users)
            await update.message.reply_text(f"Added {amt}$", reply_markup=admin_kb())
        except:
            await update.message.reply_text("Format USERID AMOUNT", reply_markup=admin_kb())
        context.user_data["wait"] = None
        return

    if wait == "set_perc":
        try:
            perc = float(txt.replace("%", ""))
            cfg = get_cfg()
            cfg["perc"] = perc
            save_file("config.json", cfg)
            await update.message.reply_text(f"Perc {perc}%", reply_markup=admin_kb())
        except:
            pass
        context.user_data["wait"] = None
        return

async def cb_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    users = load_file("users.json")
    u = users.get(str(uid), {})
    bal = u.get("balance", 0)

    if d == "vendor_panel" or d == "vendor":
        is_vendor = u.get("is_vendor", False)
        if is_vendor:
            prods = load_file("products.json")
            my_stock = len([p for p in prods.values() if p.get("owner") == uid and not p.get("sold")])
            my_sold = len([p for p in prods.values() if p.get("owner") == uid and p.get("sold")])
            earn = u.get("vendor_earn", 0)
            txt = f"VENDOR FULL Stock {my_stock} Sold {my_sold} Earn {earn}$ Bal {bal}$"
            await q.edit_message_text(txt, reply_markup=vendor_dash_kb())
        else:
            txt = f"VENDOR BUY {VENDOR_PRICE}$ Bal {bal}$"
            await q.edit_message_text(txt, reply_markup=vendor_buy_kb(bal))
        return

    if d == "buy_vendor":
        if u.get("is_vendor"):
            await q.edit_message_text("Already vendor", reply_markup=vendor_dash_kb())
            return
        if bal < VENDOR_PRICE:
            await q.edit_message_text(f"Need {VENDOR_PRICE}$ Bal {bal}$", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="top_dep")], [InlineKeyboardButton("Back", callback_data="vendor_panel")]]))
            return
        users[str(uid)]["balance"] = bal - VENDOR_PRICE
        users[str(uid)]["is_vendor"] = True
        save_file("users.json", users)
        await q.edit_message_text(f"VENDOR BOUGHT Paid {VENDOR_PRICE}$", reply_markup=vendor_dash_kb())
        return

    if d == "my_vendor_stock":
        prods = load_file("products.json")
        my = [(k, v) for k, v in prods.items() if v.get("owner") == uid and not v.get("sold")]
        msg = f"My Stock {len(my)}\n"
        kb = []
        for pid, p in my[-10:]:
            msg += f"{p['code'][:10]} {p['price']}$\n"
            kb.append([InlineKeyboardButton(f"Del {p['code'][:6]}", callback_data=f"del_vendor_{pid}")])
        if not my:
            msg = "No stock"
        kb.append([InlineKeyboardButton("Add Stock", callback_data="add_stock"), InlineKeyboardButton("Back", callback_data="vendor_panel")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("del_vendor_"):
        pid = d.replace("del_vendor_", "")
        prods = load_file("products.json")
        if pid in prods and prods[pid].get("owner") == uid:
            del prods[pid]
            save_file("products.json", prods)
            await q.edit_message_text(f"Deleted {pid}", reply_markup=vendor_dash_kb())
        return

    if d == "vendor_sales":
        prods = load_file("products.json")
        sold = [(k, v) for k, v in prods.items() if v.get("owner") == uid and v.get("sold")]
        msg = f"My Sales {len(sold)}\n"
        for pid, p in sold[-10:]:
            msg += f"{p['code'][:10]} {p['price']}$ SOLD\n"
        if not sold:
            msg = "No sales"
        await q.edit_message_text(msg, reply_markup=vendor_dash_kb())
        return

    if d == "vendor_earn":
        earn = u.get("vendor_earn", 0)
        await q.edit_message_text(f"Earnings {earn}$", reply_markup=vendor_dash_kb())
        return

    if d == "main_menu":
        await q.edit_message_text(welcome(), reply_markup=top_menu(uid == ADMIN_ID))
        return
    if d == "top_admin":
        await q.edit_message_text("ADMIN PANEL", reply_markup=admin_kb())
        return
    if d == "top_list":
        prods = load_file("products.json")
        active = [(k, v) for k, v in prods.items() if not v.get("sold")]
        if not active:
            await q.edit_message_text("NO STOCK", reply_markup=top_menu(uid == ADMIN_ID))
            return
        msg = f"LISTINGS {len(active)}\n"
        kb = []
        for pid, p in active[-10:][::-1]:
            msg += f"{p['code'][:10]} {p['price']}$\n"
            kb.append([InlineKeyboardButton(f"{p['code'][:6]} {p['price']}$", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("Filter", callback_data="top_filter")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
        return
    if d == "top_dep":
        await q.edit_message_text("DEPOSIT LTC SOL", reply_markup=top_menu(uid == ADMIN_ID))
        return
    if d == "top_profile":
        txt = f"PROFILE ID {uid} Bal {bal}$"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Vendor Panel", callback_data="vendor_panel")], [InlineKeyboardButton("Back", callback_data="main_menu")]])
        await q.edit_message_text(txt, reply_markup=kb)
        return
    if d == "top_filter":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("All", callback_data="filter_All"), InlineKeyboardButton("Giftcard", callback_data="filter_Giftcard")],
            [InlineKeyboardButton("COD 880 CP", callback_data="filter_COD")],
            [InlineKeyboardButton("Back", callback_data="main_menu")]
        ])
        await q.edit_message_text("FILTER", reply_markup=kb)
        return
    if d.startswith("filter_"):
        cat = d.replace("filter_", "")
        prods = load_file("products.json")
        if cat == "All":
            active = [(k, v) for k, v in prods.items() if not v.get("sold")]
        elif cat == "Giftcard":
            active = [(k, v) for k, v in prods.items() if not v.get("sold") and v.get("category")!= "COD"]
        elif cat == "COD":
            active = [(k, v) for k, v in prods.items() if not v.get("sold") and v.get("category") == "COD"]
        else:
            active = [(k, v) for k, v in prods.items() if not v.get("sold")]
        if not active:
            await q.edit_message_text(f"No stock {cat}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Filter", callback_data="top_filter")]]))
            return
        msg = f"{cat} {len(active)}\n"
        kb = []
        for pid, p in active[-10:][::-1]:
            kb.append([InlineKeyboardButton(f"Buy {p['price']}$", callback_data=f"view_{pid}")])
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))
        return
    if d == "my_purchases":
        pur = u.get("purchases", [])[-10:]
        msg = "MY PURCHASES\n"
        for p in pur[::-1]:
            msg += f"{p.get('code','')[:15]} {p.get('price')}$\n"
        if not pur:
            msg = "No purchases"
        await q.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="top_profile")]]))
        return
    if d == "noop":
        return
    if d == "mark_g":
        cur = context.user_data.get("mark_g", False)
        context.user_data["mark_g"] = not cur
    elif d == "mark_p":
        cur = context.user_data.get("mark_p", False)
        context.user_data["mark_p"] = not cur
    elif d == "mark_reg":
        cur = context.user_data.get("mark_reg", False)
        context.user_data["mark_reg"] = not cur
    elif d == "price_minus":
        cur = context.user_data.get("pending_price", 9)
        context.user_data["pending_price"] = max(0.5, round(cur - 1, 2))
    elif d == "price_plus":
        cur = context.user_data.get("pending_price", 9)
        context.user_data["pending_price"] = round(cur + 1, 2)
    elif d == "price_custom":
        context.user_data["wait"] = "set_price"
        await q.edit_message_text("Send price e.g. 8.5")
        return
    if d in ["mark_g", "mark_p", "mark_reg", "price_minus", "price_plus"]:
        g = context.user_data.get("mark_g", False)
        p = context.user_data.get("mark_p", False)
        reg = context.user_data.get("mark_reg", False)
        amt = context.user_data["pending_amt"]
        price = context.user_data["pending_price"]
        cat = context.user_data.get("upload_type", "Giftcard")
        code = context.user_data["pending_code"]
        await q.edit_message_text(f"Card {code[:20]} {price}$", reply_markup=mark_kb(g, p, reg, p
