import os, json, uuid, threading, requests
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6699688350"))
GITHUB_RAW_URL = os.getenv("GITHUB_RAW_URL", "https://raw.githubusercontent.com/twinlovetoma/telegram-bot/main/bot.py")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "PREMIUM FINAL LIVE"
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
    default={"perc":65,"comm":5,"auto_update":True,"version":"9.0 FINAL","github_url":GITHUB_RAW_URL,"vendor_enabled":True,"relist_enabled":True,"vendor_price":20,"relist_price":15}
    cfg=load_file("config.json", default)
    for k,v in default.items():
        if k not in cfg: cfg[k]=v
    return cfg

def get_user(uid_s):
    users=load_file("users.json")
    if uid_s not in users:
        users[uid_s]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[],"is_vendor":False}
        save_file("users.json", users)
    return users

CATEGORIES = ["Free Fire","Call of Duty 880 CP","Call of Duty Gift Card","Call of Duty Points","PUBG","PUBG UC","Amazon","Google Play","iTunes","Steam","PlayStation","Xbox","Netflix","Spotify","Other"]

def premium_header(t): return f"╔═══════════════╗\n 💎 {t} 💎\n╚═══════════════╝\n"
def user_kb(uid):
    cfg=get_cfg(); users=get_user(str(uid)); u=users.get(str(uid),{})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Latest Listings", callback_data="listings_All"), InlineKeyboardButton("🔍 Filter", callback_data="filter")],
        [InlineKeyboardButton("👤 Profile Dashboard", callback_data="prof")],
        [InlineKeyboardButton(f"🏪 Vendor {'✅' if u.get('vendor_access') else f'${cfg['vendor_price']}'}", callback_data="buy_vendor"), InlineKeyboardButton(f"🔄 Relist {'✅' if u.get('relist_access') else f'${cfg['relist_price']}'}", callback_data="buy_relist")],
        [InlineKeyboardButton("💰 Balance", callback_data="bal"), InlineKeyboardButton("💳 Deposit", callback_data="dep")],
        [InlineKeyboardButton("📜 Transactions", callback_data="hist")]
    ])
def admin_main_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')]); c=get_cfg()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Panel", callback_data="go_edit"), InlineKeyboardButton("🔄 Update Panel", callback_data="go_update")],
        [InlineKeyboardButton("🤖 AI Panel", callback_data="go_ai"), InlineKeyboardButton(f"📦 Stock: {s}", callback_data="stock")],
        [InlineKeyboardButton(f"🏪 Vendor {'ON ✅' if c.get('vendor_enabled') else 'OFF ❌'} ${c['vendor_price']}", callback_data="toggle_vendor"), InlineKeyboardButton(f"🔄 Relist {'ON ✅' if c.get('relist_enabled') else 'OFF ❌'} ${c['relist_price']}", callback_data="toggle_relist")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="add"), InlineKeyboardButton("💲 Set %", callback_data="perc")],
        [InlineKeyboardButton("💵 Add Balance", callback_data="addbal"), InlineKeyboardButton("🔄 Relist All", callback_data="relist")],
        [InlineKeyboardButton("🧑‍💼 Vendor Req", callback_data="vreq"), InlineKeyboardButton("👥 All Sellers", callback_data="sellers")],
        [InlineKeyboardButton("⏳ Pending", callback_data="orders"), InlineKeyboardButton("📊 Sales", callback_data="sales")],
        [InlineKeyboardButton("📜 Buyer History", callback_data="bhist")]
    ])
def edit_panel_kb():
    p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    return InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Stock: {s}", callback_data="stock")],[InlineKeyboardButton("⚡ EASY EDIT", callback_data="edit_list")],[InlineKeyboardButton("⬅️ Back", callback_data="go_admin")]])
def update_panel_kb():
    c=get_cfg(); return InlineKeyboardMarkup([[InlineKeyboardButton(f"Auto: {'ON ✅' if c.get('auto_update') else 'OFF ❌'}", callback_data="toggle_auto")],[InlineKeyboardButton("Update Now", callback_data="update_now"), InlineKeyboardButton("Set GitHub", callback_data="set_github")],[InlineKeyboardButton("⬅️ Back", callback_data="go_admin")]])
def ai_panel_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🎤 Bolun ki lagbe", callback_data="ai_prompt")],[InlineKeyboardButton("⬅️ Back", callback_data="go_admin")]])
def filter_kb():
    kb=[]
    for i in range(0, len(CATEGORIES), 2):
        row=[InlineKeyboardButton(CATEGORIES[i], callback_data=f"listings_{CATEGORIES[i]}")]
        if i+1 < len(CATEGORIES): row.append(InlineKeyboardButton(CATEGORIES[i+1], callback_data=f"listings_{CATEGORIES[i+1]}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("📋 All", callback_data="listings_All"), InlineKeyboardButton("⬅️ Back", callback_data="uview")])
    return InlineKeyboardMarkup(kb)
def category_edit_kb(pid):
    kb=[]
    for i in range(0, len(CATEGORIES), 2):
        row=[InlineKeyboardButton(CATEGORIES[i][:15], callback_data=f"ecat_{CATEGORIES[i]}_{pid}")]
        if i+1 < len(CATEGORIES): row.append(InlineKeyboardButton(CATEGORIES[i+1][:15], callback_data=f"ecat_{CATEGORIES[i+1]}_{pid}"))
        kb.append(row)
    kb.append([InlineKeyboardButton("⬅️ Back", callback_data=f"item_{pid}")])
    return InlineKeyboardMarkup(kb)
def after_purchase_kb(oid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Refund Request", callback_data=f"refund_{oid}"), InlineKeyboardButton("📜 Transactions", callback_data="hist")],
        [InlineKeyboardButton("🌀 ReCheck Card", callback_data=f"recheck_{oid}"), InlineKeyboardButton("🔄 ReList Card", callback_data=f"relist_one_{oid}")],
        [InlineKeyboardButton("🛒 Buy More", callback_data="listings_All"), InlineKeyboardButton("👤 Profile", callback_data="prof")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; users=get_user(str(uid))
    c=get_cfg(); p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    if uid==ADMIN_ID:
        await update.message.reply_text(premium_header("ADMIN PANEL") + f"Perc: {c['perc']}% | Stock: {s}\nVendor ${c['vendor_price']} | Relist ${c['relist_price']}", reply_markup=admin_main_kb())
    else:
        await update.message.reply_text(premium_header("BEST GIFT STORE") + f"Hi {update.effective_user.first_name}!\n💰 Bal: ${users[str(uid)].get('balance',0)} | 📦 {s} Cards\n👇 Dashboard:", reply_markup=user_kb(uid))

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip(); wait=context.user_data.get('wait'); uid=update.effective_user.id; uid_s=str(uid)
    if wait=="ai_prompt" and uid==ADMIN_ID: await update.message.reply_text(f"🤖 Saved: {txt}", reply_markup=ai_panel_kb()); context.user_data['wait']=None; return
    if wait=="set_github": c=get_cfg(); c["github_url"]=txt; save_file("config.json", c); await update.message.reply_text("✅ GitHub set", reply_markup=update_panel_kb()); context.user_data['wait']=None; return
    if wait and wait.startswith("edit_"):
        _, field, pid = wait.split("_",2); prods=load_file("products.json")
        if pid in prods:
            if field=="brand": prods[pid]['brand']=txt
            elif field=="amount": prods[pid]['amount']=txt
            elif field=="code": prods[pid]['code']=txt
            elif field=="price":
                try: prods[pid]['sell_price']=float(txt)
                except: await update.message.reply_text("Number dao!"); return
            save_file("products.json", prods); await update.message.reply_text(f"✅ {field}", reply_markup=edit_panel_kb())
        context.user_data['wait']=None; return
    if wait=="addbal":
        try:
            parts=txt.split(); uid_add=parts[0]; amt=float(parts[1])
            users=load_file("users.json")
            if uid_add not in users: users[uid_add]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[]}
            users[uid_add]["balance"]=users[uid_add].get("balance",0)+amt
            save_file("users.json", users)
            await update.message.reply_text(f"✅ Added ${amt} to {uid_add}", reply_markup=admin_main_kb())
        except: await update.message.reply_text("Format: USERID AMOUNT")
        context.user_data['wait']=None; return
    if uid!=ADMIN_ID: return
    if wait=="add":
        try:
            parts=txt.split(); brand=parts[0]; amount=parts[1]; code=" ".join(parts[2:])
            cat="Other"; low=txt.lower()
            if "gift" in low and "cod" in low: cat="Call of Duty Gift Card"
            elif "880" in low: cat="Call of Duty 880 CP"
            elif "cod" in low: cat="Call of Duty Points"
            elif "free" in low: cat="Free Fire"
            elif "pubg" in low: cat="PUBG"
            elif "amazon" in low: cat="Amazon"
            prods=load_file("products.json"); pid=str(uuid.uuid4())[:6]
            prods[pid]={"brand":brand,"amount":amount,"code":code,"sell_price":5,"sold":False,"category":cat}
            save_file("products.json", prods); await update.message.reply_text(f"✅ Added {brand} as {cat}", reply_markup=admin_main_kb())
        except: await update.message.reply_text("Format: BRAND AMOUNT CODE")
        context.user_data['wait']=None

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id; uid_s=str(uid); cfg=get_cfg()
    if d=="go_admin": p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')]); await q.edit_message_text(premium_header("ADMIN PANEL") + f"Stock: {s}", reply_markup=admin_main_kb()); return
    elif d=="go_edit": await q.edit_message_text(premium_header("EDIT PANEL"), reply_markup=edit_panel_kb()); return
    elif d=="go_update": await q.edit_message_text(premium_header("UPDATE PANEL"), reply_markup=update_panel_kb()); return
    elif d=="go_ai": await q.edit_message_text(premium_header("AI PANEL") + "Bolun ki lagbe!", reply_markup=ai_panel_kb()); return
    if d=="buy_vendor":
        users=load_file("users.json");
        if uid_s not in users: users[uid_s]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[]}
        u=users[uid_s]
        if u.get("vendor_access"): await q.edit_message_text("✅ Already Vendor!", reply_markup=user_kb(uid)); return
        if u.get("balance",0) < cfg["vendor_price"]: await q.edit_message_text(f"❌ Need ${cfg['vendor_price']}", reply_markup=user_kb(uid)); return
        u["balance"]-=cfg["vendor_price"]; u["vendor_access"]=True; u["is_vendor"]=True; users[uid_s]=u; save_file("users.json", users)
        await q.edit_message_text(premium_header("VENDOR ACTIVATED") + f"✅ ${cfg['vendor_price']} deducted!", reply_markup=user_kb(uid)); return
    if d=="buy_relist":
        users=load_file("users.json");
        if uid_s not in users: users[uid_s]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[]}
        u=users[uid_s]
        if u.get("relist_access"): await q.edit_message_text("✅ Already Relist!", reply_markup=user_kb(uid)); return
        if u.get("balance",0) < cfg["relist_price"]: await q.edit_message_text(f"❌ Need ${cfg['relist_price']}", reply_markup=user_kb(uid)); return
        u["balance"]-=cfg["relist_price"]; u["relist_access"]=True; users[uid_s]=u; save_file("users.json", users)
        await q.edit_message_text(premium_header("RELIST ACTIVATED") + f"✅ ${cfg['relist_price']} deducted!", reply_markup=user_kb(uid)); return
    if d=="prof":
        users=load_file("users.json"); u=users.get(uid_s, {}); pur=u.get("purchases", [])
        v="✅ Enabled" if u.get("vendor_access") else f"❌ Disabled (${cfg['vendor_price']})"
        r="✅ Enabled" if u.get("relist_access") else f"❌ Disabled (${cfg['relist_price']})"
        txt=premium_header("MY PROFILE") + f"🆔 @{q.from_user.username or 'N/A'} | ID: {uid}\n💰 ${u.get('balance',0)} | Purchase: {len(pur)}\n\n🏪 Vendor: {v}\n🔄 Relist: {r}\n\n📜 Last 5:\n"
        for o in pur[-5:][::-1]: txt+=f"• {o.get('brand')} {o.get('amount')} ${o.get('sell_price')} {o.get('status')}\n"
        if not pur: txt+="No purchase\n"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Latest", callback_data="listings_All"), InlineKeyboardButton("🔍 Filter", callback_data="filter")],[InlineKeyboardButton(f"🏪 Buy Vendor ${cfg['vendor_price']}", callback_data="buy_vendor"), InlineKeyboardButton(f"🔄 Buy Relist ${cfg['relist_price']}", callback_data="buy_relist")],[InlineKeyboardButton("📜 Transactions", callback_data="hist"), InlineKeyboardButton("⬅️ Back", callback_data="uview")]])); return
    if d.startswith("listings_"):
        cat=d.replace("listings_",""); prods=load_file("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold')] if cat=="All" else [(k,v) for k,v in prods.items() if not v.get('sold') and v.get('category')==cat]
        if not active:
            counts={}
            for v in prods.values():
                if not v.get('sold'): counts[v.get('category','Other')]=counts.get(v.get('category','Other'),0)+1
            txt=premium_header(f"{cat} EMPTY") + "❌ No stock\n" + "\n".join([f"• {k}: {v}" for k,v in counts.items()]) or "No stock"
            await q.edit_message_text(txt, reply_markup=filter_kb()); return
        txt=premium_header(f"{cat} ({len(active)})") + ""
        kb=[]
        for pid,p in active[-12:][::-1]: txt+=f"💎 {p['brand']} {p['amount']} ${p['sell_price']}\n"; kb.append([InlineKeyboardButton(f"💎 {p['brand']} {p['amount']} ${p['sell_price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("🔍 Filter", callback_data="filter"), InlineKeyboardButton("⬅️ Back", callback_data="uview")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d=="filter": await q.edit_message_text(premium_header("FILTER") + f"{len(CATEGORIES)} Cats", reply_markup=filter_kb())
    elif d.startswith("view_"):
        pid=d.replace("view_",""); prods=load_file("products.json")
        if pid not in prods: await q.edit_message_text("Not found", reply_markup=filter_kb()); return
        p=prods[pid]
        await q.edit_message_text(premium_header("CARD DETAILS") + f"🎁 {p['brand']}\n💲 {p['amount']}\n💰 ${p['sell_price']}\n📦 {p.get('category','Other')}\n🆔 {pid}\n", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Buy ${p['sell_price']}", callback_data=f"buy_{pid}")],[InlineKeyboardButton("⬅️ Back", callback_data=f"listings_{p.get('category','All')}")]]))
    elif d.startswith("buy_"):
        pid=d.replace("buy_",""); prods=load_file("products.json")
        if pid not in prods or prods[pid].get('sold'): await q.edit_message_text("❌ Already sold!", reply_markup=user_kb(uid)); return
        p=prods[pid]; orders=load_file("orders.json"); users=load_file("users.json")
        if uid_s not in users: users[uid_s]={"balance":0,"vendor_access":False,"relist_access":False,"purchases":[]}
        oid=str(uuid.uuid4())[:6]
        o={"buyer_id":uid,"brand":p['brand'],"amount":p['amount'],"code":p['code'],"sell_price":p['sell_price'],"category":p.get('category','Other'),"status":"completed","id":oid,"time":datetime.now().strftime("%Y-%m-%d %H:%M")}
        orders[oid]=o; save_file("orders.json", orders)
        users[uid_s].setdefault("purchases", []).append(o); save_file("users.json", users)
        prods[pid]['sold']=True; save_file("products.json", prods)
        await q.edit_message_text(premium_header("PURCHASE SUCCESS") + f"✅ Order: {oid}\n🎁 {p['brand']} {p['amount']}\n💰 ${p['sell_price']}\n\n🔑 CODE:\n`{p['code']}`\n⏰ {o['time']}\n", reply_markup=after_purchase_kb(oid))
    elif d.startswith("refund_"):
        oid=d.replace("refund_",""); refunds=load_file("refunds.json", {}); refunds[oid]={"user_id":uid,"time":datetime.now().strftime("%Y-%m-%d %H:%M"),"status":"pending"}; save_file("refunds.json", refunds)
        await q.edit_message_text(premium_header("REFUND REQUESTED") + f"Order {oid} pending\nAdmin 24h e check korbe!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌀 ReCheck", callback_data=f"recheck_{oid}"), InlineKeyboardButton("📜 Transactions", callback_data="hist")]]))
    elif d.startswith("recheck_"):
        oid=d.replace("recheck_",""); orders=load_file("orders.json"); o=orders.get(oid, {})
        await q.edit_message_text(premium_header("RECHECK CARD") + f"🌀 Checking...\n🆔 {oid}\n🎁 {o.get('brand','')} {o.get('amount','')}\n🔑 `{o.get('code','')}`\n💰 ${o.get('sell_price','')}\n📊 ✅ Valid\n", reply_markup=after_purchase_kb(oid))
    elif d.startswith("relist_one_"):
        oid=d.replace("relist_one_",""); users=load_file("users.json"); u=users.get(uid_s, {})
        if not u.get("relist_access"): await q.edit_message_text(premium_header("RELIST LOCKED") + f"❌ Need ${cfg['relist_price']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"🔄 Buy ${cfg['relist_price']}", callback_data="buy_relist")],[InlineKeyboardButton("⬅️ Back", callback_data="hist")]])); return
        orders=load_file("orders.json"); o=orders.get(oid)
        if o:
            prods=load_file("products.json"); pid=str(uuid.uuid4())[:6]
            prods[pid]={"brand":o['brand'],"amount":o['amount'],"code":o['code'],"sell_price":o['sell_price'],"sold":False,"category":o.get('category','Other')}
            save_file("products.json", prods)
            await q.edit_message_text(premium_header("RELISTED") + f"✅ New ID {pid}", reply_markup=after_purchase_kb(oid))
    elif d=="bal": users=load_file("users.json"); await q.edit_message_text(premium_header("BALANCE") + f"💰 ${users.get(uid_s,{}).get('balance',0)}", reply_markup=user_kb(uid))
    elif d=="dep": await q.edit_message_text(premium_header("DEPOSIT") + "LTC / SOL / Binance", reply_markup=user_kb(uid))
    elif d=="hist":
        users=load_file("users.json"); pur=users.get(uid_s,{}).get("purchases", [])
        txt=premium_header("TRANSACTIONS") + f"Total: {len(pur)}\n"
        for o in pur[-10:][::-1]: txt+=f"• {o.get('brand')} {o.get('amount')} ${o.get('sell_price')} [{o.get('id')}]\n"
        if not pur: txt+="No transactions"
        kb=[]
        for o in pur[-5:][::-1]: kb.append([InlineKeyboardButton(f"🌀 {o.get('brand')} {o.get('id')}", callback_data=f"recheck_{o.get('id')}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="uview")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d=="help": await q.edit_message_text(premium_header("HELP") + "/start", reply_markup=user_kb(uid))
    elif d=="uview":
        if uid==ADMIN_ID: p=load_file("products.json"); s=len([x for x in p.values() if not x.get('sold')]); await q.edit_message_text(premium_header("ADMIN PANEL") + f"Stock: {s}", reply_markup=admin_main_kb())
        else: await q.edit_message_text(premium_header("WELCOME") + f"Hi {q.from_user.first_name}!", reply_markup=user_kb(uid))
    elif uid==ADMIN_ID:
        if d=="add": context.user_data['wait']="add"; await q.edit_message_text(premium_header("ADD STOCK") + "BRAND AMOUNT CODE")
        elif d=="perc": await q.edit_message_text(f"Perc: {cfg['perc']}%", reply_markup=admin_main_kb())
        elif d=="stock":
            p=load_file("products.json"); counts={}
            for v in p.values():
                if not v.get('sold'): counts[v.get('category','Other')]=counts.get(v.get('category','Other'),0)+1
            txt=premium_head
