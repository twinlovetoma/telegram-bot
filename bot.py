import os, json, uuid, threading
from datetime import datetime, date
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6699688350"))
STOCK_CHANNEL = int(os.getenv("STOCK_CHANNEL", "-1001234567890"))
LTC_ADDR = os.getenv("LTC_ADDR", "ltc1qexample")
SOL_ADDR = os.getenv("SOL_ADDR", "solExample")

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "MEGA FIXED - OK"

@flask_app.route('/health')
def health():
    return "OK"

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))

threading.Thread(target=run_flask, daemon=True).start()

def load_file(f, d=None):
    if d is None:
        d = {}
    if not os.path.exists(f):
        return d
    try:
        with open(f, 'r') as j:
            return json.load(j)
    except:
        return d

def save_file(f, d):
    with open(f, 'w') as j:
        json.dump(j, d, indent=2)

def get_cfg():
    return load_file("config.json", {"perc": 65, "ltc": LTC_ADDR, "sol": SOL_ADDR})

def user_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Latest", callback_data="listings_All"), InlineKeyboardButton("Filter", callback_data="filter")],
        [InlineKeyboardButton("Balance", callback_data="bal"), InlineKeyboardButton("Deposit", callback_data="dep")],
        [InlineKeyboardButton("Profile", callback_data="prof")],
        [InlineKeyboardButton("History", callback_data="hist"), InlineKeyboardButton("Help", callback_data="help")]
    ])

def admin_kb():
    p = load_file("products.json")
    s = len([x for x in p.values() if not x.get('sold')])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Stock {s}", callback_data="stock"), InlineKeyboardButton("Add Stock", callback_data="add")],
        [InlineKeyboardButton("EASY EDIT", callback_data="edit_list")],
        [InlineKeyboardButton("Orders", callback_data="orders"), InlineKeyboardButton("Deposits", callback_data="deps")],
        [InlineKeyboardButton("User View", callback_data="uview")]
    ])

def filter_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("All", callback_data="listings_All"), InlineKeyboardButton("Free Fire", callback_data="listings_Free Fire")],
        [InlineKeyboardButton("COD 880 CP", callback_data="listings_Call of Duty 880 CP"), InlineKeyboardButton("PUBG", callback_data="listings_PUBG")],
        [InlineKeyboardButton("Amazon", callback_data="listings_Amazon"), InlineKeyboardButton("Other", callback_data="listings_Other")],
        [InlineKeyboardButton("Back", callback_data="uview")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users = load_file("users.json")
    if str(uid) not in users:
        users[str(uid)] = {"balance": 0, "daily": None, "total_buy": 0}
        save_file("users.json", users)
    if uid == ADMIN_ID:
        await update.message.reply_text("ADMIN - MEGA FIXED - All features + Easy Edit 1 click", reply_markup=admin_kb())
    else:
        bal = users[str(uid)]['balance']
        await update.message.reply_text(f"Welcome {update.effective_user.first_name}! Bal: ${bal}", reply_markup=user_kb())

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    wait = context.user_data.get('wait')

    if wait and wait.startswith("act_"):
        oid = wait.replace("act_", "")
        orders = load_file("orders.json")
        if oid in orders:
            orders[oid]['activation'] = txt
            orders[oid]['status'] = 'pending'
            save_file("orders.json", orders)
            await update.message.reply_text(f"Submitted Act: {txt}", reply_markup=user_kb())
            try:
                kb = [[InlineKeyboardButton("Approve + PDF", callback_data=f"app_{oid}"), InlineKeyboardButton("Reject", callback_data=f"rej_{oid}")]]
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"Order {oid} {orders[oid]['brand']} Act: {txt}", reply_markup=InlineKeyboardMarkup(kb))
            except:
                pass
        context.user_data['wait'] = None
        return

    if wait and wait.startswith("trx_"):
        coin = wait.split("_")[1]
        deps = load_file("deposits.json", [])
        did = str(uuid.uuid4())[:6]
        deps.append({"id": did, "user_id": uid, "coin": coin, "trx": txt, "status": "pending"})
        save_file("deposits.json", deps)
        await update.message.reply_text(f"{coin} TRX {txt} submitted!", reply_markup=user_kb())
        context.user_data['wait'] = None
        return

    if wait and wait.startswith("edit_"):
        try:
            _, field, pid = wait.split("_", 2)
            prods = load_file("products.json")
            if pid in prods:
                if field == "brand":
                    prods[pid]['brand'] = txt
                elif field == "amount":
                    prods[pid]['amount'] = txt
                elif field == "code":
                    prods[pid]['code'] = txt
                elif field == "price":
                    prods[pid]['sell_price'] = float(txt)
                elif field == "cat":
                    prods[pid]['category'] = txt
                save_file("products.json", prods)
                await update.message.reply_text(f"Updated {field} to {txt}", reply_markup=admin_kb())
        except:
            pass
        context.user_data['wait'] = None
        return

    if wait == "search":
        prods = load_file("products.json")
        res = [(k, v) for k, v in prods.items() if txt.lower() in v['brand'].lower() and not v.get('sold')]
        if not res:
            await update.message.reply_text("No match!", reply_markup=user_kb())
        else:
            t = f"Search {txt}:\n"
            kb = []
            for pid, p in res[:10]:
                t += f"{p['brand']} {p['amount']} ${p['sell_price']}\n"
                kb.append([InlineKeyboardButton(f"{p['brand']} ${p['sell_price']}", callback_data=f"view_{pid}")])
            kb.append([InlineKeyboardButton("Back", callback_data="uview")])
            await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb))
        context.user_data['wait'] = None
        return

    if uid!= ADMIN_ID:
        return

    if wait == "add":
        try:
            parts = txt.split()
            brand = parts[0]
            amount = parts[1]
            code = " ".join(parts[2:])
            prods = load_file("products.json")
            pid = str(uuid.uuid4())[:6]
            cfg = get_cfg()
            try:
                price = float(''.join(filter(str.isdigit, amount))) * cfg['perc'] / 100
            except:
                price = 5
            prods[pid] = {"brand": brand, "amount": amount, "code": code, "sell_price": round(price, 2), "sold": False, "category": "Other"}
            save_file("products.json", prods)
            await update.message.reply_text(f"Added {brand} {amount} ${round(price, 2)}", reply_markup=admin_kb())
        except:
            await update.message.reply_text("Format: BRAND AMOUNT CODE")
        context.user_data['wait'] = None

    elif wait == "perc":
        try:
            cfg = get_cfg()
            cfg['perc'] = float(txt)
            save_file("config.json", cfg)
            await update.message.reply_text(f"{cfg['perc']}% set", reply_markup=admin_kb())
        except:
            await update.message.reply_text("Ex: 65")
        context.user_data['wait'] = None

    elif wait == "addbal":
        try:
            uid2, amt = txt.split()
            amt = float(amt)
            users = load_file("users.json")
            if uid2 not in users:
                users[uid2] = {"balance": 0, "daily": None, "total_buy": 0}
            users[uid2]['balance'] += amt
            save_file("users.json", users)
            await update.message.reply_text(f"${amt} to {uid2}", reply_markup=admin_kb())
        except:
            await update.message.reply_text("USERID AMOUNT")
        context.user_data['wait'] = None

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    cfg = get_cfg()

    if d.startswith("listings_"):
        cat = d.replace("listings_", "")
        prods = load_file("products.json")
        if cat == "All":
            active = [(k, v) for k, v in prods.items() if not v.get('sold')]
        else:
            active = [(k, v) for k, v in prods.items() if not v.get('sold') and v.get('category') == cat]
        if not active:
            await q.edit_message_text(f"No stock in {cat}", reply_markup=filter_kb())
            return
        txt = f"{cat} ({len(active)}):\n"
        kb = []
        for pid, p in active[-10:][::-1]:
            txt += f"{p['brand']} {p['amount']} ${p['sell_price']}\n"
            kb.append([InlineKeyboardButton(f"{p['brand']} {p['amount']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("Filter", callback_data="filter")])
        kb.append([InlineKeyboardButton("Back", callback_data="uview")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d == "filter":
        await q.edit_message_text("Filter:", reply_markup=filter_kb())
        return

    if d.startswith("view_"):
        pid = d.replace("view_", "")
        prods = load_file("products.json")
        if pid not in prods or prods[pid].get('sold'):
            await q.edit_message_text("Sold!", reply_markup=user_kb())
            return
        p = prods[pid]
        txt = f"Brand: {p['brand']}\nAmount: {p['amount']}\nPrice: ${p['sell_price']}\nCategory: {p.get('category','Other')}"
        kb = [[InlineKeyboardButton(f"Place Order ${p['sell_price']}", callback_data=f"buy_{pid}")], [InlineKeyboardButton("Back", callback_data="listings_All")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("buy_"):
        pid = d.replace("buy_", "")
        prods = load_file("products.json")
        if pid not in prods or prods[pid].get('sold'):
            await q.edit_message_text("Sold!", reply_markup=user_kb())
            return
        orders = load_file("orders.json")
        oid = str(uuid.uuid4())[:6]
        orders[oid] = {"buyer_id": uid, "buyer": q.from_user.first_name, "product_id": pid, "brand": prods[pid]['brand'], "amount": prods[pid]['amount'], "code": prods[pid]['code'], "sell_price": prods[pid]['sell_price'], "category": prods[pid].get('category','Other'), "status": "wait", "id": oid}
        save_file("orders.json", orders)
        context.user_data['wait'] = f"act_{oid}"
        await q.edit_message_text(f"Order {oid} Created!\nSend ID Pass TRX\nEx: ID:123 Pass:abc TRX:tx123", reply_markup=user_kb())
        return

    if d == "dep":
        await q.edit_message_text("Deposit:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("LTC", callback_data="dep_ltc"), InlineKeyboardButton("SOL", callback_data="dep_sol")], [InlineKeyboardButton("Back", callback_data="uview")]]))
        return

    if d == "dep_ltc":
        addr = cfg.get('ltc', LTC_ADDR)
        await q.edit_message_text(f"LTC {addr} Min $5", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Submit TRX", callback_data="sub_ltc")], [InlineKeyboardButton("Cancel", callback_data="dep")]]))
        return

    if d == "dep_sol":
        addr = cfg.get('sol', SOL_ADDR)
        await q.edit_message_text(f"SOL {addr}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Submit TRX", callback_data="sub_sol")], [InlineKeyboardButton("Cancel", callback_data="dep")]]))
        return

    if d == "sub_ltc":
        context.user_data['wait'] = 'trx_LTC'
        await q.edit_message_text("Send LTC TRX ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="dep")]]))
        return

    if d == "sub_sol":
        context.user_data['wait'] = 'trx_SOL'
        await q.edit_message_text("Send SOL TRX ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="dep")]]))
        return

    if d == "bal":
        users = load_file("users.json")
        bal = users.get(str(uid), {}).get('balance', 0)
        await q.edit_message_text(f"Balance: ${bal}", reply_markup=user_kb())
        return

    if d == "prof":
        await q.edit_message_text(f"ID: {uid} Name: {q.from_user.first_name}", reply_markup=user_kb())
        return

    if d == "hist":
        orders = load_file("orders.json")
        txt = "History:\n"
        for oid, o in orders.items():
            if str(o['buyer_id']) == str(uid):
                txt += f"{oid} {o['brand']} {o['status']}\n"
        if txt == "History:\n":
            txt = "No history"
        await q.edit_message_text(txt, reply_markup=user_kb())
        return

    if d == "help":
        await q.edit_message_text("All Features: Filter Free Fire/COD, Deposit QR, ID+Pass+TRX, Easy Edit 1 click", reply_markup=user_kb())
        return

    if d == "uview":
        await q.edit_message_text(f"Welcome {q.from_user.first_name}!", reply_markup=user_kb())
        return

    if d == "search":
        context.user_data['wait'] = 'search'
        await q.edit_message_text("Send brand name:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="uview")]]))
        return

    if uid!= ADMIN_ID:
        return

    if d == "add":
        context.user_data['wait'] = "add"
        await q.edit_message_text("Send: BRAND AMOUNT CODE\nEx: Amazon 10 ABC123", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
        return

    if d == "edit_list":
        prods = load_file("products.json")
        active = [(k, v) for k, v in prods.items() if not v.get('sold')]
        if not active:
            await q.edit_message_text("No stock!", reply_markup=admin_kb())
            return
        txt = f"EASY EDIT - {len(active)} items\n"
        kb = []
        for pid, p in active[-10:][::-1]:
            txt += f"ID:{pid[:6]} {p['brand']} {p['amount']} ${p['sell_price']} [{p.get('category','')}]\n"
            kb.append([InlineKeyboardButton(f"{p['brand']} {p['amount']}", callback_data=f"item_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("item_"):
        pid = d.replace("item_", "")
        prods = load_file("products.json")
        if pid not in prods:
            await q.edit_message_text("Not found", reply_markup=admin_kb())
            return
        p = prods[pid]
        txt = f"EDIT ITEM\nID: {pid}\nBrand: {p['brand']}\nAmount: {p['amount']}\nPrice: ${p['sell_price']}\nCode: {p['code']}\nCategory: {p.get('category','Other')}"
        kb = [[InlineKeyboardButton("Brand", callback_data=f"eb_{pid}"), InlineKeyboardButton("Amount", callback_data=f"ea_{pid}")], [InlineKeyboardButton("Price", callback_data=f"ep_{pid}"), InlineKeyboardButton("Code", callback_data=f"ec_{pid}")], [InlineKeyboardButton("Free Fire", callback_data=f"ecat_Free Fire_{pid}"), InlineKeyboardButton("COD 880 CP", callback_data=f"ecat_Call of Duty 880 CP_{pid}")], [InlineKeyboardButton("DELETE", callback_data=f"del_{pid}")], [InlineKeyboardButton("Back List", callback_data="edit_list")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("eb_"):
        pid = d.replace("eb_", "")
        context.user_data['wait'] = f"edit_brand_{pid}"
        await q.edit_message_text(f"New Brand for {pid[:6]}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"item_{pid}")]]))
        return

    if d.startswith("ea_"):
        pid = d.replace("ea_", "")
        context.user_data['wait'] = f"edit_amount_{pid}"
        await q.edit_message_text("New Amount:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"item_{pid}")]]))
        return

    if d.startswith("ep_"):
        pid = d.replace("ep_", "")
        context.user_data['wait'] = f"edit_price_{pid}"
        await q.edit_message_text("New Price:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"item_{pid}")]]))
        return

    if d.startswith("ec_"):
        pid = d.replace("ec_", "")
        context.user_data['wait'] = f"edit_code_{pid}"
        await q.edit_message_text("New Code:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"item_{pid}")]]))
        return

    if d.startswith("ecat_"):
        tmp = d.replace("ecat_", "")
        cat, pid = tmp.rsplit("_", 1)
        prods = load_file("products.json")
        if pid in prods:
            prods[pid]['category'] = cat
            save_file("products.json", prods)
            await q.edit_message_text(f"Category -> {cat} for {pid[:6]}", reply_markup=admin_kb())
        return

    if d.startswith("del_"):
        pid = d.replace("del_", "")
        prods = load_file("products.json")
        if pid in prods:
            del prods[pid]
            save_file("products.json", prods)
            await q.edit_message_text(f"Deleted {pid[:6]}", reply_markup=admin_kb())
        return

    if d == "back":
        await q.edit_message_text("ADMIN - MEGA FIXED", reply_markup=admin_kb())
        return

    if d == "stock":
        prods = load_file("products.json")
        s = len([x for x in prods.values() if not x.get('sold')])
        await q.edit_message_text(f"Stock: {s}", reply_markup=admin_kb())
        return

    if d == "perc":
        context.user_data['wait'] = "perc"
        await q.edit_message_text("Send % Ex: 65", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
        return

    if d == "addbal":
        context.user_data['wait'] = "addbal"
        await q.edit_message_text("USERID AMOUNT", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
        return

    if d == "orders":
        orders = load_file("orders.json")
        txt = "Pending:\n"
        kb = []
        for oid, o in orders.items():
            if 'pending' in o['status'] or o['status'] == 'wait':
                txt += f"{oid} {o['brand']} Act:{o.get('activation','')[:8]}\n"
                kb.append([InlineKeyboardButton(f"Approve {oid}", callback_data=f"app_{oid}"), InlineKeyboardButton(f"Reject {oid}", callback_data=f"rej_{oid}")])
        if not kb:
            txt = "No orders"
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d == "deps":
        deps = load_file("deposits.json", [])
        txt = "Deposits:\n"
        kb = []
        for dep in deps:
            if dep['status'] == 'pending':
                txt += f"{dep['id']} {dep['coin']}\n"
                kb.append([InlineKeyboardButton(f"Approve {dep['id']}", callback_data=f"dapp_{dep['id']}"), InlineKeyboardButton(f"Reject {dep['id']}", callback_data=f"drej_{dep['id']}")])
        if not kb:
            txt = "No deposits"
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
        return

    if d.startswith("app_"):
        oid = d.replace("app_", "")
        orders = load_file("orders.json")
        if oid in orders:
            orders[oid]['status'] = 'approved'
            save_file("orders.json", orders)
            prods = load_file("products.json")
            pid = orders[oid]['product_id']
            if pid in prods:
                prods[pid]['sold'] = True
                save_file("products.json", prods)
            await q.edit_message_text(f"Approved {oid}!", reply_markup=admin_kb())
        return

    if d.startswith("rej_"):
        oid = d.replace("rej_", "")
        orders = load_file("orders.json")
        if oid in orders:
            orders[oid]['status'] = 'rejected'
            save_file("orders.json", orders)
            await q.edit_message_text(f"Rejected {oid}", reply_markup=admin_kb())
        return

    if d.startswith("dapp_"):
        did = d.replace("dapp_", "")
        deps = load_file("deposits.json", [])
        users = load_file("users.json")
        for dep in deps:
            if dep['id'] == did:
                dep['status'] = 'approved'
                us = str(dep['user_id'])
                if us not in users:
                    users[us] = {"balance": 0, "daily": None, "total_buy": 0}
                users[us]['balance'] += 10
                save_file("users.json", users)
                save_file("deposits.json", deps)
                await q.edit_message_text(f"Deposit {did} +$10", reply_markup=admin_kb())
                break
        return

    if d.startswith("drej_"):
        did = d.replace("drej_", "")
        deps = load_file("deposits.json", [])
        for dep in deps:
            if dep['id'] == did:
                dep['status'] = 'rejected'
                save_file("deposits.json", deps)
                await q.edit_message_text(f"Deposit {did} rejected", reply_markup=admin_kb())
                break
        return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    print("MEGA FIXED Bot Started - No Error")
    app.run_polling()

if __name__ == "__main__":
    main()
