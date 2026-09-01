import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "@your_channel")
STOCK_CHANNEL = os.getenv("STOCK_CHANNEL", "https://t.me/your_channel")
CHECKER_BOT = "@XprepaidCheckerBot"
VENDOR_PRICE = 15

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v78 FULL LIVE"
@flask_app.route('/health')
def health(): return "OK"

def load_file(name):
    try:
        if os.path.exists(name):
            with open(name, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_file(name, data):
    with open(name, "w") as f:
        json.dump(data, f, indent=2)

def get_user(uid):
    users = load_file("users.json")
    s = str(uid)
    if s not in users:
        users[s] = {"balance": 0, "purchases": [], "is_vendor": False, "sales": 0, "earn": 0}
        save_file("users.json", users)
    return users

def get_cfg():
    cfg = load_file("config.json")
    if not cfg:
        cfg = {"perc": 39, "comm": 5}
    return cfg

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
        [InlineKeyboardButton("Seller Dashboard", callback_data="vendor_panel")],
        [InlineKeyboardButton("Listings", callback_data="list"), InlineKeyboardButton("Profile", callback_data="profile")],
        [InlineKeyboardButton("Stock Channel", url=STOCK_CHANNEL)]
    ])

def profile_menu(uid=0, bal=0):
    checker = CHECKER_BOT.replace("@", "")
    link = f"https://t.me/{checker}?start=check_{uid}_{bal}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Deposit Funds", callback_data="dep_funds"), InlineKeyboardButton("Balance Checker", url=link)],
        [InlineKeyboardButton("Order History", callback_data="order_hist"), InlineKeyboardButton("Back", callback_data="main")]
    ])

def admin_kb():
    cfg = get_cfg()
    prods = load_file("products.json")
    stock = len([x for x in prods.values() if not x.get("sold")])
    perc = cfg.get("perc", 39)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Stock:{stock}", callback_data="noop"), InlineKeyboardButton(f"{perc}%", callback_data="set_perc")],
        [InlineKeyboardButton("Add Stock", callback_data="add_gift"), InlineKeyboardButton("Add Balance", callback_data="add_bal")],
        [InlineKeyboardButton("Users", callback_data="users_list"), InlineKeyboardButton("Orders", callback_data="pending_orders")],
        [InlineKeyboardButton("Back", callback_data="main")]
    ])

def vendor_dash_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Giftcard", callback_data="add_gift")],
        [InlineKeyboardButton("My Stock", callback_data="my_stock"), InlineKeyboardButton("My Sales", callback_data="my_sales")],
        [InlineKeyboardButton("Back", callback_data="main")]
    ])

def mark_kb(g, p, reg, price, orig):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'ON' if g else 'OFF'}", callback_data="mark_g"), InlineKeyboardButton(f"P {'ON' if p else 'OFF'}", callback_data="mark_p"), InlineKeyboardButton(f"{'REG' if reg else 'UNREG'}", callback_data="mark_reg")],
        [InlineKeyboardButton("-", callback_data="price_minus"), InlineKeyboardButton("39% ON", callback_data="mark_39"), InlineKeyboardButton("+", callback_data="price_plus")],
        [InlineKeyboardButton(f"SAVE ${price}", callback_data="mark_save")],
        [InlineKeyboardButton("Cancel", callback_data="main")]
    ])

async def post_to_stock_channel(context, product, pid):
    try:
        code = product["code"]
        masked = f"{code[:4]}...."
        price = product["price"]
        avl = product.get("orig", "?")
        g = "ON" if product.get("g") else "OFF"
        p = "ON" if product.get("p") else "OFF"
        reg = "REG" if product.get("reg") else "UNREG"
        txt = f"NEW STOCK\n{masked} avl ${avl} ${price} G {g} P {p} {reg}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Buy Now", url=f"https://t.me/{context.bot.username}?start=buy_{pid}")]])
        await context.bot.send_message(chat_id=STOCK_CHANNEL_ID, text=txt, reply_markup=kb)
    except Exception as e:
        print(e)

async def start_cmd(update, context):
    uid = update.effective_user.id
    get_user(uid)
    cfg = get_cfg()
    users = load_file("users.json")
    bal = users.get(str(uid), {}).get("balance", 0)
    stock = len([x for x in load_file("products.json").values() if not x.get("sold")])
    await update.message.reply_text(f"BAL:${bal} STOCK:{stock} RATE:{cfg['perc']}%", reply_markup=top_menu(uid == ADMIN_ID))

async def admin_cmd(update, context):
    if update.effective_user.id!= ADMIN_ID:
        return
    cfg = get_cfg()
    await update.message.reply_text(f"ADMIN {cfg['perc']}%", reply_markup=admin_kb())

async def msg_h(update, context):
    txt = update.message.text or ""
    uid = update.effective_user.id
    if txt.startswith("/"):
        return
    wait = context.user_data.get("wait")
    if wait == "add_stock":
        amt = get_amount(txt)
        if amt == 0:
            await update.message.reply_text("Send card like 4511... $25 - last dollar is avl")
            return
        perc = get_cfg().get("perc", 39)
        calc = round(amt * perc / 100, 2)
        context.user_data.update({"code": txt, "amt": amt, "price": calc, "g": True, "p": False, "reg": True, "wait": "marking"})
        await update.message.reply_text(f"{txt[:4]}.... avl ${amt}", reply_markup=mark_kb(True, False, True, calc, amt))
        return
    if wait == "set_perc_custom":
        try:
            perc = float(txt.replace("%", ""))
            cfg = get_cfg()
            cfg["perc"] = perc
            save_file("config.json", cfg)
            await update.message.reply_text(f"Perc set {perc}%", reply_markup=admin_kb())
        except:
            pass
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
            await update.message.reply_text(f"Added ${amt} to {uid_t}", reply_markup=admin_kb())
        except:
            await update.message.reply_text("Format USERID AMOUNT", reply_markup=admin_kb())
        context.user_data["wait"] = None
        return

async def cb_h(update, context):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    users = get_user(uid)
    u = users.get(str(uid), {})
    bal = u.get("balance", 0)

    if d == "main":
        cfg = get_cfg()
        stock = len([x for x in load_file("products.json").values() if not x.get("sold")])
        await q.edit_message_text(f"BAL:${bal} STOCK:{stock} RATE:{cfg['perc']}%", reply_markup=top_menu(uid == ADMIN_ID))
        return
    if d == "profile":
        await q.edit_message_text(f"ID:{uid} BAL:${bal}", reply_markup=profile_menu(uid, bal))
        return
    if d == "dep_funds":
        await q.edit_message_text("Deposit - Contact Admin", reply_markup=profile_menu(uid, bal))
        return
    if d == "order_hist":
        await q.edit_message_text("No orders yet", reply_markup=profile_menu(uid, bal))
        return
    if d == "list":
        prods = load_file("products.json")
        active = [(k, v) for k, v in prods.items() if not v.get("sold")]
        kb = [[InlineKeyboardButton(f"{p['code'][:8]} ${p['price']}", callback_data=f"view_{pid}")] for pid, p in active[-10:][::-1]]
        kb.append([InlineKeyboardButton("Back", callback_data="main")])
        await q.edit_message_text(f"List {len(active)}", reply_markup=InlineKeyboardMarkup(kb))
        return
    if d == "admin":
        cfg = get_cfg()
        await q.edit_message_text(f"ADMIN {cfg['perc']}%", reply_markup=admin_kb())
        return
    if d == "vendor_panel":
        await q.edit_message_text("Seller Dashboard", reply_markup=vendor_dash_kb())
        return
    if d == "my_stock":
        prods = load_file("products.json")
        my = [(k, v) for k, v in prods.items() if v.get("owner") == uid and not v.get("sold")]
        msg = f"My Stock {len(my)}\n"
        for pid, p in my[-10:]:
            msg += f"{p['code'][:8]} ${p['price']}\n"
        await q.edit_message_text(msg, reply_markup=vendor_dash_kb())
        return
    if d == "my_sales":
        await q.edit_message_text("No sales", reply_markup=vendor_dash_kb())
        return
    if d == "add_gift":
        context.user_data["wait"] = "add_stock"
        await q.edit_message_text("SEND CARD LIKE 4511... $25 - last $ is avl")
        return
    if d == "set_perc":
        context.user_data["wait"] = "set_perc_custom"
        await q.edit_message_text("Send new perc e.g. 39")
        return
    if d == "add_bal":
        context.user_data["wait"] = "add_bal"
        await q.edit_message_text("Send USERID AMOUNT e.g. 12345 10")
        return
    if d == "users_list":
        users_all = load_file("users.json")
        msg = f"Users {len(users_all)}\n"
        for k in list(users_all.keys())[-10:]:
            msg += f"{k}\n"
        await q.edit_message_text(msg, reply_markup=admin_kb())
        return
    if d == "pending_orders":
        await q.edit_message_text("No pending", reply_markup=admin_kb())
        return
    if d == "noop":
        return
    if d in ["mark_g", "mark_p", "mark_reg", "price_minus", "price_plus", "mark_39"]:
        if d == "mark_g":
            context.user_data["g"] = not context.user_data.get("g", False)
        if d == "mark_p":
            context.user_data["p"] = not context.user_data.get("p", False)
        if d == "mark_reg":
            context.user_data["reg"] = not context.user_data.get("reg", False)
        if d == "price_minus":
            context.user_data["price"] = max(0.01, round(context.user_data.get("price", 0.3) - 0.05, 2))
        if d == "price_plus":
            context.user_data["price"] = round(context.user_data.get("price", 0.3) + 0.05, 2)
        if d == "mark_39":
            avl = context.user_data.get("amt", 0)
            perc = get_cfg().get("perc", 39)
            context.user_data["price"] = round(avl * perc / 100, 2)
        g = context.user_data.get("g")
        p = context.user_data.get("p")
        reg = context.user_data.get("reg")
        price = context.user_data["price"]
        orig = context.user_data.get("amt", 0)
        await q.edit_message_text(f"{context.user_data.get('code','')[:4]}.... avl ${orig}", reply_markup=mark_kb(g, p, reg, price, orig))
        return
    if d == "mark_save":
        price = context.user_data["price"]
        code = context.user_data["code"]
        orig = context.user_data.get("amt", 0)
        prods = load_file("products.json")
        pid = str(uuid.uuid4())[:6]
        prods[pid] = {"code": code, "orig": orig, "price": price, "sold": False, "owner": uid, "g": context.user_data.get("g"), "p": context.user_data.get("p"), "reg": context.user_data.get("reg")}
        save_file("products.json", prods)
        context.user_data["wait"] = None
        try:
            checker = CHECKER_BOT.replace("@", "")
            link = f"https://t.me/{checker}?start=stock_{pid}_{ADMIN_ID}_{orig}"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Check in Checker Bot", url=link)]])
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"STOCK ADDED BY ADMIN {ADMIN_ID} - {code[:4]}.... avl ${orig} -> ${price} PID:{pid}", reply_markup=kb)
            txt2 = f"NEW STOCK {code[:4]}.... avl ${orig} ${price} G {'ON' if context.user_data.get('g') else 'OFF'} P {'ON' if context.user_data.get('p') else 'OFF'}"
            kb2 = InlineKeyboardMarkup([[InlineKeyboardButton("Buy Now", url=f"https://t.me/{context.bot.username}?start=buy_{pid}")]])
            await context.bot.send_message(chat_id=STOCK_CHANNEL_ID, text=txt2, reply_markup=kb2)
        except Exception as e:
            print(e)
        await q.edit_message_text(f"Saved {code[:4]}.... avl ${orig} -> ${price}", reply_markup=admin_kb())
        return
    if d.startswith("view_"):
        pid = d.replace("view_", "")
        p = load_file("products.json").get(pid)
        if not p:
            await q.edit_message_text("Sold out", reply_markup=top_menu())
            return
        await q.edit_message_text(f"{p['code'][:30]} avl ${p.get('orig')} -> ${p['price']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="list")]]))
        return

async def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(cb_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    await app.initialize()
    await app.start()
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.updater.start_polling(drop_pending_updates=True)
    print("BOT STARTED v78")
    while True:
        await asyncio.sleep(3600)

def run_thread():
    asyncio.run(run_bot())

if __name__ == "__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
