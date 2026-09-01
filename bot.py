import os, json, uuid, threading, traceback, requests
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6699688350"))
GITHUB_RAW_URL = os.getenv("GITHUB_RAW_URL", "")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "AUTO-UPDATE BOT LIVE - FINAL"
@flask_app.route('/health')
def health(): return "OK"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000))), daemon=True).start()

def load_file(f,d=None):
    if d is None: d={}
    if not os.path.exists(f): return d
    try:
        with open(f,'r') as file: return json.load(file)
    except: return d

def save_file(f,d):
    with open(f,'w') as file: json.dump(d, file, indent=2)

def get_cfg():
    return load_file("config.json", {"perc":65,"comm":5,"auto_update":True,"version":"1.0","github_url":GITHUB_RAW_URL})

def check_and_auto_update(context):
    try:
        cfg = get_cfg()
        if not cfg.get("auto_update", True): return
        url = cfg.get("github_url") or GITHUB_RAW_URL
        if not url: return
        r = requests.get(url, timeout=15)
        if r.status_code!= 200: return
        remote_code = r.text
        with open(__file__, 'r', encoding='utf-8') as f:
            local_code = f.read()
        if remote_code.strip()!= local_code.strip() and len(remote_code) > 1000 and "BOT_TOKEN" in remote_code:
            with open(__file__, 'w', encoding='utf-8') as f:
                f.write(remote_code)
            cfg["version"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_file("config.json", cfg)
            print("AUTO UPDATE DONE - RESTARTING")
            os._exit(0)
    except Exception as e:
        print(f"Auto update error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users = load_file("users.json")
    if str(uid) not in users:
        users[str(uid)] = {"balance":0}
        save_file("users.json", users)
    cfg = get_cfg()
    p = load_file("products.json")
    s = len([x for x in p.values() if not x.get('sold')])
    if uid == ADMIN_ID:
        status = "ON ✅" if cfg.get("auto_update") else "OFF ❌"
        await update.message.reply_text(
            f"👑 AUTO-UPDATE BOT FINAL\nPerc: {cfg['perc']}%\nStock: {s}\nVersion: {cfg.get('version','1.0')}\nAuto-Update: {status}\n\n✅ EASY EDIT + AUTO UPDATE READY",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"Stock: {s}", callback_data="stock"), InlineKeyboardButton("Add Stock", callback_data="add")],
                [InlineKeyboardButton("EASY EDIT 1-Click", callback_data="edit_list")],
                [InlineKeyboardButton(f"Auto-Update: {status}", callback_data="toggle_auto")],
                [InlineKeyboardButton("Update Now", callback_data="update_now")],
                [InlineKeyboardButton("Set GitHub URL", callback_data="set_github")],
                [InlineKeyboardButton("Pending Orders", callback_data="orders")]
            ])
        )
    else:
        await update.message.reply_text(f"Welcome {update.effective_user.first_name}!")

async def debug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_cfg()
    txt = f"🔍 STATUS\nVersion: {cfg.get('version')}\nAuto: {'ON' if cfg.get('auto_update') else 'OFF'}\nGitHub: {cfg.get('github_url') or GITHUB_RAW_URL or 'Not set'}\n\n/setgithub https://raw.githubusercontent.com/.../bot.py"
    await update.message.reply_text(txt)

async def setgithub_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /setgithub https://raw.githubusercontent.com/username/repo/main/bot.py")
        return
    url = context.args[0]
    cfg = get_cfg()
    cfg["github_url"] = url
    save_file("config.json", cfg)
    await update.message.reply_text(f"✅ GitHub URL set!\n{url}")

async def update_now_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Checking for update...")
    check_and_auto_update(context)
    await update.message.reply_text("✅ Check done! Jodi notun code thake bot 30 sec e restart hobe.")

async def autoupdate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_cfg()
    cfg["auto_update"] = not cfg.get("auto_update", True)
    save_file("config.json", cfg)
    await update.message.reply_text(f"Auto-Update {'ON ✅' if cfg['auto_update'] else 'OFF ❌'}")

async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    doc = update.message.document
    if doc and doc.file_name.endswith(".py"):
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive("new_bot.py")
        with open("new_bot.py","r",encoding="utf-8") as f:
            code = f.read()
        if "BOT_TOKEN" in code and len(code) > 1000:
            os.replace("new_bot.py", __file__)
            cfg = get_cfg()
            cfg["version"] = datetime.now().strftime("%Y-%m-%d %H:%M file")
            save_file("config.json", cfg)
            await update.message.reply_text("✅ bot.py updated from Telegram! Restarting... 30 sec por /start dao!")
            os._exit(0)
        else:
            await update.message.reply_text("❌ Valid bot.py na!")

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    wait = context.user_data.get('wait')
    if wait == "set_github":
        cfg = get_cfg()
        cfg["github_url"] = txt
        save_file("config.json", cfg)
        await update.message.reply_text(f"✅ GitHub URL set: {txt}")
        context.user_data['wait'] = None
        return
    if wait and wait.startswith("edit_"):
        try:
            _, field, pid = wait.split("_",2)
            prods = load_file("products.json")
            if pid in prods:
                if field == "brand": prods[pid]['brand'] = txt
                elif field == "amount": prods[pid]['amount'] = txt
                elif field == "code": prods[pid]['code'] = txt
                elif field == "price": prods[pid]['sell_price'] = float(txt)
                elif field == "cat": prods[pid]['category'] = txt
                save_file("products.json", prods)
                await update.message.reply_text(f"Updated {field} -> {txt}")
        except: pass
        context.user_data['wait'] = None
        return
    if uid!= ADMIN_ID: return
    if wait == "add":
        try:
            parts = txt.split()
            brand = parts[0]
            amount = parts[1]
            code = " ".join(parts[2:])
            prods = load_file("products.json")
            pid = str(uuid.uuid4())[:6]
            prods[pid] = {"brand":brand,"amount":amount,"code":code,"sell_price":5,"sold":False,"category":"Other"}
            save_file("products.json", prods)
            await update.message.reply_text(f"Added {brand} {amount}")
        except:
            await update.message.reply_text("Format: BRAND AMOUNT CODE")
        context.user_data['wait'] = None

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    if d == "edit_list":
        prods = load_file("products.json")
        active = [(k,v) for k,v in prods.items() if not v.get('sold')]
        if not active:
            await q.edit_message_text("No stock! Add Stock chap dao")
            return
        txt = f"EASY EDIT - {len(active)} items\nTap to edit:\n"
        kb = []
        for pid,p in active[-10:][::-1]:
            txt += f"{pid[:6]} {p['brand']} {p['amount']} ${p['sell_price']} [{p.get('category','Other')}]\n"
            kb.append([InlineKeyboardButton(f"{p['brand']} {p['amount']}", callback_data=f"item_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("item_"):
        pid = d.replace("item_","")
        prods = load_file("products.json")
        if pid not in prods:
            await q.edit_message_text("Not found")
            return
        p = prods[pid]
        txt = f"EDIT ID:{pid}\nBrand: {p['brand']}\nAmount: {p['amount']}\nPrice: ${p['sell_price']}\nCode: {p['code']}\nCat: {p.get('category','Other')}"
        kb = [
            [InlineKeyboardButton("Brand", callback_data=f"eb_{pid}"), InlineKeyboardButton("Amount", callback_data=f"ea_{pid}")],
            [InlineKeyboardButton("Price", callback_data=f"ep_{pid}"), InlineKeyboardButton("Code", callback_data=f"ec_{pid}")],
            [InlineKeyboardButton("Free Fire", callback_data=f"ecat_Free Fire_{pid}"), InlineKeyboardButton("COD 880 CP", callback_data=f"ecat_Call of Duty 880 CP_{pid}")],
            [InlineKeyboardButton("DELETE", callback_data=f"del_{pid}")],
            [InlineKeyboardButton("Back", callback_data="edit_list")]
        ]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("eb_"):
        pid = d.replace("eb_","")
        context.user_data['wait'] = f"edit_brand_{pid}"
        await q.edit_message_text("New Brand likho:")
    elif d.startswith("ea_"):
        pid = d.replace("ea_","")
        context.user_data['wait'] = f"edit_amount_{pid}"
        await q.edit_message_text("New Amount likho:")
    elif d.startswith("ep_"):
        pid = d.replace("ep_","")
        context.user_data['wait'] = f"edit_price_{pid}"
        await q.edit_message_text("New Price likho (ex: 5.5):")
    elif d.startswith("ec_"):
        pid = d.replace("ec_","")
        context.user_data['wait'] = f"edit_code_{pid}"
        await q.edit_message_text("New Code likho:")
    elif d.startswith("ecat_"):
        tmp = d.replace("ecat_","")
        cat, pid = tmp.rsplit("_",1)
        prods = load_file("products.json")
        prods[pid]['category'] = cat
        save_file("products.json", prods)
        await q.edit_message_text(f"Category -> {cat} set!")
    elif d.startswith("del_"):
        pid = d.replace("del_","")
        prods = load_file("products.json")
        if pid in prods:
            del prods[pid]
            save_file("products.json", prods)
        await q.edit_message_text("Deleted!")
    elif d == "toggle_auto":
        cfg = get_cfg()
        cfg["auto_update"] = not cfg.get("auto_update", True)
        save_file("config.json", cfg)
        await q.edit_message_text(f"Auto-Update {'ON ✅' if cfg['auto_update'] else 'OFF ❌'} - /start dao")
    elif d == "update_now":
        await q.edit_message_text("🔄 Checking...")
        check_and_auto_update(context)
        await q.edit_message_text("✅ Checked! 30 sec por restart hobe jodi update thake")
    elif d == "set_github":
        context.user_data['wait'] = "set_github"
        await q.edit_message_text("GitHub RAW URL dao:\nEx: https://raw.githubusercontent.com/username/repo/main/bot.py")
    elif d == "add":
        context.user_data['wait'] = "add"
        await q.edit_message_text("Send: BRAND AMOUNT CODE\nEx: Amazon 10 CODE123")
    elif d == "stock":
        p = load_file("products.json")
        s = len([x for x in p.values() if not x.get('sold')])
        await q.edit_message_text(f"Stock: {s}")
    elif d == "back":
        cfg = get_cfg()
        p = load_file("products.json")
        s = len([x for x in p.values() if not x.get('sold')])
        status = "ON ✅" if cfg.get("auto_update") else "OFF ❌"
        await q.edit_message_text(f"Admin Panel\nStock: {s}\nAuto: {status}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("EASY EDIT", callback_data="edit_list")],[InlineKeyboardButton(f"Auto: {status}", callback_data="toggle_auto")],[InlineKeyboardButton("Update Now", callback_data="update_now")]]))
    elif d == "orders":
        orders = load_file("orders.json")
        txt = "Orders:\n"
        for oid,o in list(orders.items())[-10:]:
            txt += f"{oid} {o['brand']} {o['status']}\n"
        if txt == "Orders:\n": txt = "No orders"
        await q.edit_message_text(txt)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug", debug_cmd))
    app.add_handler(CommandHandler("setgithub", setgithub_cmd))
    app.add_handler(CommandHandler("update_now", update_now_cmd))
    app.add_handler(CommandHandler("autoupdate", autoupdate_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.Document.ALL, doc_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    # Auto check every 1 hour
    if app.job_queue:
        app.job_queue.run_repeating(lambda ctx: check_and_auto_update(ctx), interval=3600, first=60)
    print("FINAL AUTO-UPDATE BOT LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
