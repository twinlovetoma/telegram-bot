import os, json, uuid, threading, re, asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "@your_channel")
STOCK_CHANNEL = os.getenv("STOCK_CHANNEL", "https://t.me/your_channel")
CHECKER_BOT = "@XprepaidCheckerBot"
CHECKER_BOT_ID = os.getenv("CHECKER_BOT_ID", "@XprepaidCheckerBot") # chaile numeric ID dite paro

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "v79 AUTO CHECKER FIXED"
@flask_app.route('/health')
def health(): return "OK"

def load_file(name):
    try:
        if os.path.exists(name):
            with open(name, "r") as f: return json.load(f)
    except: pass
    return {}
def save_file(name, data):
    with open(name, "w") as f: json.dump(f, data, indent=2)
def get_user(uid):
    users = load_file("users.json")
    s=str(uid)
    if s not in users:
        users[s]={"balance":0,"purchases":[],"is_vendor":False,"sales":0,"earn":0}
        save_file("users.json", users)
    return users
def get_cfg():
    cfg=load_file("config.json")
    if not cfg: cfg={"perc":39,"comm":5}
    return cfg
def get_amount(text):
    m=re.findall(r"\$([0-9]+\.?[0-9]*)", text)
    if m:
        try: return float(m[-1])
        except: pass
    return 0.0

def top_menu(admin=False):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Seller Dashboard", callback_data="vendor_panel")],
        [InlineKeyboardButton("Listings", callback_data="list"), InlineKeyboardButton("Profile", callback_data="profile")],
        [InlineKeyboardButton("Stock Channel", url=STOCK_CHANNEL)]
    ])
def profile_menu(uid=0, bal=0):
    checker=CHECKER_BOT.replace("@","")
    link=f"https://t.me/{checker}?start=check_{uid}_{bal}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Deposit Funds", callback_data="dep_funds"), InlineKeyboardButton("Balance Checker", url=link)],
        [InlineKeyboardButton("Back", callback_data="main")]
    ])
def admin_kb():
    cfg=get_cfg()
    prods=load_file("products.json")
    stock=len([x for x in prods.values() if not x.get("sold")])
    perc=cfg.get("perc",39)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Stock:{stock}", callback_data="noop"), InlineKeyboardButton(f"{perc}%", callback_data="set_perc")],
        [InlineKeyboardButton("Add Stock", callback_data="add_gift"), InlineKeyboardButton("Add Balance", callback_data="add_bal")],
        [InlineKeyboardButton("Back", callback_data="main")]
    ])
def vendor_dash_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Add Giftcard", callback_data="add_gift")],[InlineKeyboardButton("My Stock", callback_data="my_stock")],[InlineKeyboardButton("Back", callback_data="main")]])
def mark_kb(g,p,reg,price,orig):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"G {'ON' if g else 'OFF'}", callback_data="mark_g"), InlineKeyboardButton(f"P {'ON' if p else 'OFF'}", callback_data="mark_p"), InlineKeyboardButton(f"{'REG' if reg else 'UNREG'}", callback_data="mark_reg")],
        [InlineKeyboardButton("-", callback_data="price_minus"), InlineKeyboardButton("39% ON", callback_data="mark_39"), InlineKeyboardButton("+", callback_data="price_plus")],
        [InlineKeyboardButton(f"SAVE ${price}", callback_data="mark_save")],
        [InlineKeyboardButton("Cancel", callback_data="main")]
    ])

async def post_to_stock_channel(context, product, pid):
    try:
        code=product["code"]; masked=f"{code[:4]}...."; price=product["price"]; avl=product.get("orig","?"); g="ON" if product.get("g") else "OFF"; p="ON" if product.get("p") else "OFF"
        txt=f"NEW STOCK\n{masked} avl ${avl} ${price} G {g} P {p}"
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("Buy Now", url=f"https://t.me/{context.bot.username}?start=buy_{pid}")]])
        await context.bot.send_message(chat_id=STOCK_CHANNEL_ID, text=txt, reply_markup=kb)
    except Exception as e: print(e)

# --- AUTO SEND TO CHECKER BOT ---
async def auto_send_to_checker(context, code, pid, orig, price):
    full_details = (
        f"AUTO STOCK CHECK\n"
        f"ADMIN_ID: {ADMIN_ID}\n"
        f"PID: {pid}\n"
        f"CODE: {code}\n"
        f"AVL: ${orig}\n"
        f"SELL: ${price}\n"
        f"G: {'ON' if context.user_data.get('g') else 'OFF'} P: {'ON' if context.user_data.get('p') else 'OFF'}\n"
        f"TIME: AUTO"
    )
    try:
        # 1. Try send directly to checker bot username/ID
        await context.bot.send_message(chat_id=CHECKER_BOT_ID, text=full_details)
        print(f"Auto sent to checker {CHECKER_BOT_ID}")
    except Exception as e:
        print(f"Checker direct send fail {e}")
        # 2. Fallback - send to admin as log that would be checked
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"[FALLBACK CHECK LOG]\n{full_details}\n\nChecker bot e auto jacche na - Checker bot ke main bot er sathe ekta group e add koro, tahole 100% auto jabe.")
        except: pass

async def start_cmd(update, context):
    uid=update.effective_user.id; get_user(uid); cfg=get_cfg(); bal=load_file("users.json").get(str(uid),{}).get("balance",0); stock=len([x for x in load_file("products.json").values() if not x.get("sold")])
    await update.message.reply_text(f"BAL:${bal} STOCK:{stock} RATE:{cfg['perc']}%", reply_markup=top_menu(uid==ADMIN_ID))

async def admin_cmd(update, context):
    if update.effective_user.id!=ADMIN_ID: return
    cfg=get_cfg(); await update.message.reply_text(f"ADMIN {cfg['perc']}%", reply_markup=admin_kb())

async def msg_h(update, context):
    txt=update.message.text or ""
    if txt.startswith("/"): return
    wait=context.user_data.get("wait")
    if wait=="add_stock":
        amt=get_amount(txt)
        if amt==0:
            await update.message.reply_text("Send like 4511... $25 - last $ is avl"); return
        perc=get_cfg().get("perc",39); calc=round(amt*perc/100,2)
        context.user_data.update({"code":txt,"amt":amt,"price":calc,"g":True,"p":False,"reg":True,"wait":"marking"})
        await update.message.reply_text(f"{txt[:4]}.... avl ${amt}", reply_markup=mark_kb(True,False,True,calc,amt)); return
    if wait=="set_perc_custom":
        try:
            perc=float(txt.replace("%","")); cfg=get_cfg(); cfg["perc"]=perc; save_file("config.json", cfg); await update.message.reply_text(f"Perc {perc}%", reply_markup=admin_kb())
        except: pass
        context.user_data["wait"]=None; return
    if wait=="add_bal":
        try:
            uid_t, amt = txt.split()[0], float(txt.split()[1]); users=load_file("users.json")
            if uid_t not in users: users[uid_t]={"balance":0,"purchases":[],"is_vendor":False,"sales":0,"earn":0}
            users[uid_t]["balance"]=users[uid_t].get("balance",0)+amt; save_file("users.json", users); await update.message.reply_text(f"Added ${amt}", reply_markup=admin_kb())
        except: await update.message.reply_text("USERID AMOUNT", reply_markup=admin_kb())
        context.user_data["wait"]=None; return

async def cb_h(update, context):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id; users=get_user(uid); u=users.get(str(uid),{}); bal=u.get("balance",0)
    if d=="main":
        cfg=get_cfg(); stock=len([x for x in load_file("products.json").values() if not x.get("sold")]); await q.edit_message_text(f"BAL:${bal} STOCK:{stock} RATE:{cfg['perc']}%", reply_markup=top_menu(uid==ADMIN_ID)); return
    if d=="profile":
        await q.edit_message_text(f"ID:{uid} BAL:${bal}", reply_markup=profile_menu(uid,bal)); return
    if d=="list":
        prods=load_file("products.json"); active=[(k,v) for k,v in prods.items() if not v.get("sold")]
        if not active: await q.edit_message_text("No listings", reply_markup=top_menu(uid==ADMIN_ID)); return
        kb=[]
        for pid,p in active[-15:][::-1]:
            masked=f"{p['code'][:4]}.... avl ${p.get('orig','?')} -> ${p['price']}"
            kb.append([InlineKeyboardButton(masked, callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="main")])
        await q.edit_message_text(f"Listings {len(active)}", reply_markup=InlineKeyboardMarkup(kb)); return
    if d.startswith("view_"):
        pid=d.replace("view_",""); p=load_file("products.json").get(pid)
        if not p or p.get("sold"): await q.edit_message_text("Sold out", reply_markup=top_menu(uid==ADMIN_ID)); return
        masked=f"{p['code'][:4]}...."; avl=p.get('orig','?'); price=p['price']
        # GLITCH FIX - FULL CODE HIDE
        txt=f"Gift Card\n{masked} avl ${avl}\nPrice: ${price}\nPurchase korle full code pabe"
        kb=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy ${price}", callback_data=f"buy_{pid}")],[InlineKeyboardButton("Back", callback_data="list")]])
        await q.edit_message_text(txt, reply_markup=kb); return
    if d=="admin": cfg=get_cfg(); await q.edit_message_text(f"ADMIN {cfg['perc']}%", reply_markup=admin_kb()); return
    if d=="vendor_panel": await q.edit_message_text("Seller Dashboard", reply_markup=vendor_dash_kb()); return
    if d=="add_gift": context.user_data["wait"]="add_stock"; await q.edit_message_text("SEND CARD LIKE 4511... $25 - last $ is avl"); return
    if d=="set_perc": context.user_data["wait"]="set_perc_custom"; await q.edit_message_text("Send new perc e.g. 39"); return
    if d=="add_bal": context.user_data["wait"]="add_bal"; await q.edit_message_text("USERID AMOUNT"); return
    if d=="noop": return
    if d in ["mark_g","mark_p","mark_reg","price_minus","price_plus","mark_39"]:
        if d=="mark_g": context.user_data["g"]=not context.user_data.get("g",False)
        if d=="mark_p": context.user_data["p"]=not context.user_data.get("p",False)
        if d=="mark_reg": context.user_data["reg"]=not context.user_data.get("reg",False)
        if d=="price_minus": context.user_data["price"]=max(0.01, round(context.user_data.get("price",0.3)-0.05,2))
        if d=="price_plus": context.user_data["price"]=round(context.user_data.get("price",0.3)+0.05,2)
        if d=="mark_39": avl=context.user_data.get('amt',0); perc=get_cfg().get('perc',39); context.user_data["price"]=round(avl*perc/100,2)
        g=context.user_data.get("g"); p=context.user_data.get("p"); reg=context.user_data.get("reg"); price=context.user_data["price"]; orig=context.user_data.get("amt",0)
        await q.edit_message_text(f"{context.user_data.get('code','')[:4]}.... avl ${orig}", reply_markup=mark_kb(g,p,reg,price,orig)); return
    if d=="mark_save":
        price=context.user_data["price"]; code=context.user_data["code"]; orig=context.user_data.get("amt",0)
        prods=load_file("products.json"); pid=str(uuid.uuid4())[:6]
        prods[pid]={"code":code,"orig":orig,"price":price,"sold":False,"owner":uid,"g":context.user_data.get("g"),"p":context.user_data.get("p"),"reg":context.user_data.get("reg")}
        save_file("products.json", prods); context.user_data["wait"]=None
        # STOCK CHANNEL POST (MASKED)
        await post_to_stock_channel(context, prods[pid], pid)
        # AUTO CHECKER - FULL DETAILS WITH ADMIN ID - NO BUTTON
        await auto_send_to_checker(context, code, pid, orig, price)
        await q.edit_message_text(f"✅ Saved & Auto Sent to Checker\n{code[:4]}.... avl ${orig} -> ${price}\nPID:{pid}\nAdmin:{ADMIN_ID}\n\nStock channel e masked post gese", reply_markup=admin_kb())
        return
    if d.startswith("buy_"):
        pid=d.replace("buy_",""); p=load_file("products.json").get(pid)
        if not p or p.get("sold"): await q.edit_message_text("Sold out", reply_markup=top_menu(uid==ADMIN_ID)); return
        masked=f"{p['code'][:4]}...."; await q.edit_message_text(f"Confirm Buy?\n{masked} avl ${p.get('orig')} -> ${p['price']}\nBal:${bal}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Confirm", callback_data=f"confirm_buy_{pid}")],[InlineKeyboardButton("Back", callback_data="list")]])); return
    if d.startswith("confirm_buy_"):
        pid=d.replace("confirm_buy_",""); prods=load_file("products.json"); p=prods.get(pid)
        if not p or p.get("sold"): await q.edit_message_text("Sold out", reply_markup=top_menu(uid==ADMIN_ID)); return
        users_all=load_file("users.json"); s=str(uid)
        if users_all[s].get("balance",0) < p["price"]: await q.edit_message_text(f"Need ${p['price']}", reply_markup=top_menu()); return
        users_all[s]["balance"]-=p["price"]; save_file("users.json", users_all)
        prods[pid]["sold"]=True; save_file("products.json", prods)
        # After purchase, send full code + auto send to checker with buyer ID
        try:
            checker=CHECKER_BOT.replace("@","")
            link=f"https://t.me/{checker}?start=item_{pid}_{uid}"
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("Go to Checker", url=link)]])
            await context.bot.send_message(chat_id=uid, text=f"✅ Bought!\nCode: {p['code']}\navl ${p.get('orig')} Paid ${p['price']}", reply_markup=kb)
            # Also auto log purchase to checker bot
            await context.bot.send_message(chat_id=CHECKER_BOT_ID, text=f"PURCHASE\nBUYER:{uid}\nADMIN:{ADMIN_ID}\nPID:{pid}\nCODE:{p['code']}\nAVL:{p.get('orig')} SELL:{p['price']}")
        except: pass
        await q.edit_message_text(f"✅ Purchased {p['code'][:4]}....", reply_markup=top_menu(uid==ADMIN_ID)); return

async def run_bot():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd)); app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(cb_h)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_h))
    await app.initialize(); await app.start(); await app.bot.delete_webhook(drop_pending_updates=True)
    await app.updater.start_polling(drop_pending_updates=True)
    print("v79 LIVE");
    while True: await asyncio.sleep(3600)

def run_thread(): asyncio.run(run_bot())
if __name__=="__main__":
    threading.Thread(target=run_thread, daemon=True).start()
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
