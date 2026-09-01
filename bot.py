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

CATEGORIES = ["Free Fire","Call of Duty 880 CP","PUBG","Amazon","Google","Other"]

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "MEGA ULTIMATE - All Features - Meta AI"
@flask_app.route('/health')
def health(): return "OK"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000))), daemon=True).start()

def load(f,d=None):
    if d is None: d={}
    if not os.path.exists(f): return d
    try:
        with open(f,'r') as j: return json.load(j)
    except: return d
def save(f,d):
    with open(f,'w') as j: json.dump(j, d, indent=2)
def cfg(): return load("config.json", {"perc":65,"ltc":LTC_ADDR,"sol":SOL_ADDR})

def make_txt(o,a,t):
    p=f"/tmp/Invoice_{o['id']}.txt"
    txt=f"Invoice: {o['id']}\nDate: {datetime.now()}\nBrand: {o['brand']} {o['amount']}\nCategory: {o.get('category','Other')}\nPrice: ${o['sell_price']}\nBuyer: {o['buyer']} {o['buyer_id']}\nActivation: {a}\nTRX: {t}\nCode: {o['code']}\nWarranty: 24h\nMeta AI"
    with open(p,'w',encoding='utf-8') as f: f.write(txt)
    return p

def ai_reply(t):
    tl=t.lower()
    if any(x in tl for x in ["kivabe","koto","bangla","valo"]):
        return f"🤖 AI Bangla: '{t}'\nSob ache: Filter Free Fire/COD 880 CP, Search, Sort, Deposit LTC/SOL QR+TRX+Cancel, Buy ID+Pass+TRX, TXT+PDF, Vendor, Transfer, Redeem, Daily, Referral, Edit Stock 1 click!"
    else:
        return f"🤖 AI English: '{t}'\nAll features: Filter, Search, Sort, Deposit QR+TRX+Cancel, Order ID+Pass+TRX, TXT auto + PDF manual, Vendor Dashboard, Transfer, Redeem, Daily, Referral, Leaderboard, Sales/Buyer History, Easy Edit!"

def user_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Latest", callback_data="listings_All"), InlineKeyboardButton("🎯 Filter", callback_data="filter")],
        [InlineKeyboardButton("💰 Balance", callback_data="bal"), InlineKeyboardButton("💵 Deposit", callback_data="dep")],
        [InlineKeyboardButton("👤 Profile", callback_data="prof"), InlineKeyboardButton("🏪 Vendor", callback_data="vdash")],
        [InlineKeyboardButton("🔄 Transfer", callback_data="trans"), InlineKeyboardButton("🎁 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("🎁 Daily", callback_data="daily"), InlineKeyboardButton("🔗 Referral", callback_data="ref")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="lead"), InlineKeyboardButton("🤖 AI Chat", callback_data="ai")],
        [InlineKeyboardButton("📜 History", callback_data="hist"), InlineKeyboardButton("🆘 Help", callback_data="help")]
    ])

def admin_kb():
    p=load("products.json"); s=len([x for x in p.values() if not x.get('sold')])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Stock {s}", callback_data="stock"), InlineKeyboardButton("➕ Add Stock", callback_data="add")],
        [InlineKeyboardButton("✏️ EASY EDIT", callback_data="edit_list"), InlineKeyboardButton("🔄 Relist", callback_data="relist")],
        [InlineKeyboardButton("💲 Set %", callback_data="perc"), InlineKeyboardButton("💵 Add Balance", callback_data="addbal")],
        [InlineKeyboardButton("⏳ Orders", callback_data="orders"), InlineKeyboardButton("💳 Deposits", callback_data="deps")],
        [InlineKeyboardButton("🧑‍💼 Vendor Req", callback_data="vreq"), InlineKeyboardButton("👥 Sellers", callback_data="sellers")],
        [InlineKeyboardButton("📊 Sales", callback_data="sales"), InlineKeyboardButton("📜 Buyer Hist", callback_data="bhist")],
        [InlineKeyboardButton("⬅️ User View", callback_data="uview")]
    ])

def filter_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 All", callback_data="listings_All"), InlineKeyboardButton("🔥 Free Fire", callback_data="listings_Free Fire")],
        [InlineKeyboardButton("🎯 COD 880 CP", callback_data="listings_Call of Duty 880 CP"), InlineKeyboardButton("🎮 PUBG", callback_data="listings_PUBG")],
        [InlineKeyboardButton("🛒 Amazon", callback_data="listings_Amazon"), InlineKeyboardButton("📦 Other", callback_data="listings_Other")],
        [InlineKeyboardButton("💲 Low-High", callback_data="sort"), InlineKeyboardButton("🔍 Search", callback_data="search")],
        [InlineKeyboardButton("⬅️ Back", callback_data="uview")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; users=load("users.json")
    if str(uid) not in users: users[str(uid)]={"balance":0,"is_vendor":False,"referrals":0,"daily":None,"total_buy":0}; save("users.json", users)
    if uid==ADMIN_ID:
        await update.message.reply_text("👑 MEGA ADMIN - ALL FEATURES\n\n✏️ Easy Edit: 1 click e Brand/Amount/Price/Code/Category/Delete\n📦 Filter, Search, Sort, Deposit QR+TRX+Cancel, ID+Pass+TRX, PDF manual, Vendor, Transfer, Redeem, Daily, Referral, Sales/Buyer History sob ache!", reply_markup=admin_kb())
    else:
        await update.message.reply_text(f"🎉 Welcome {update.effective_user.first_name}!\n🎁 MEGA STORE - All Features\nBal: ${users[str(uid)]['balance']}", reply_markup=user_kb())

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=ADMIN_ID: return
    wait=context.user_data.get('wait')
    if wait and wait.startswith("pdf_"):
        oid=wait.replace("pdf_",""); orders=load("orders.json")
        if oid in orders:
            try:
                await context.bot.send_message(chat_id=orders[oid]['buyer_id'], text=f"✅ Order {oid} Completed! PDF from Admin:")
                await context.bot.send_document(chat_id=orders[oid]['buyer_id'], document=update.message.document.file_id, caption=f"📄 Invoice {oid} Warranty 24h")
                await update.message.reply_text(f"✅ PDF sent to {orders[oid]['buyer_id']} for {oid}!", reply_markup=admin_kb())
            except Exception as e: await update.message.reply_text(f"❌ {e}")
            context.user_data['wait']=None

async def msg_h(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip(); uid=update.effective_user.id; wait=context.user_data.get('wait')

    if not wait and uid!=ADMIN_ID and len(txt)>2 and not txt.startswith('/'):
        if any(w in txt.lower() for w in ["hi","hello","help","kivabe","how","price","ai"]):
            await update.message.reply_text(ai_reply(txt), reply_markup=user_kb()); return

    if wait and wait.startswith("act_"):
        oid=wait.replace("act_",""); orders=load("orders.json")
        if oid in orders:
            trx=""; act=txt
            if "trx" in txt.lower(): parts=txt.split(); trx=parts[-1]; act=" ".join(parts[:-1])
            orders[oid]['activation']=act; orders[oid]['trx']=trx; orders[oid]['status']='pending'; save("orders.json", orders)
            p=make_txt(orders[oid], act, trx)
            await update.message.reply_text(f"✅ Submitted! Act: {act} TRX: {trx}\nTXT auto!", reply_markup=user_kb())
            try:
                await context.bot.send_document(chat_id=uid, document=open(p,'rb'), filename=f"Invoice_{oid}.txt")
                kb=[[InlineKeyboardButton("✅ Approve + PDF", callback_data=f"app_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{oid}")]]
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 Order {oid}\n{orders[oid]['brand']} {orders[oid]['amount']} [{orders[oid].get('category','')}]\nAct: {act}\nTRX: {trx}\nBuyer: {orders[oid]['buyer']}", reply_markup=InlineKeyboardMarkup(kb))
            except: pass
        context.user_data['wait']=None; return

    if wait and wait.startswith("trx_"):
        coin=wait.split("_")[1]; deps=load("deposits.json", []); did=str(uuid.uuid4())[:6]
        deps.append({"id":did,"user_id":uid,"coin":coin,"trx":txt,"status":"pending","username":str(uid)}); save("deposits.json", deps)
        await update.message.reply_text(f"✅ {coin} TRX {txt} submitted!", reply_markup=user_kb())
        try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"💳 {did} {coin} {uid} {txt}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅", callback_data=f"dapp_{did}"), InlineKeyboardButton("❌", callback_data=f"drej_{did}")]]))
        except: pass
        context.user_data['wait']=None; return

    if wait and wait.startswith("edit_"):
        try:
            _, field, pid = wait.split("_",2)
            prods=load("products.json")
            if pid in prods:
                if field=="brand": prods[pid]['brand']=txt
                elif field=="amount": prods[pid]['amount']=txt
                elif field=="code": prods[pid]['code']=txt
                elif field=="price": prods[pid]['sell_price']=float(txt)
                elif field=="cat": prods[pid]['category']=txt
                save("products.json", prods)
                await update.message.reply_text(f"✅ {field} → {txt} (ID:{pid[:6]})", reply_markup=admin_kb())
        except: pass
        context.user_data['wait']=None; return

    if wait=="trans":
        try: to_id, amt = txt.split(); amt=float(amt); users=load("users.json")
        except: await update.message.reply_text("Format: USERID AMOUNT"); return
        if users[str(uid)]['balance']<amt: await update.message.reply_text("❌ Low balance!"); return
        if to_id not in users: users[to_id]={"balance":0,"is_vendor":False,"referrals":0,"daily":None,"total_buy":0}
        users[str(uid)]['balance']-=amt; users[to_id]['balance']+=amt; save("users.json", users)
        await update.message.reply_text(f"✅ ${amt} to {to_id}", reply_markup=user_kb()); context.user_data['wait']=None; return

    if wait=="redeem":
        codes=load("redeem.json", {"FREE5":5})
        if txt in codes: users=load("users.json"); users[str(uid)]['balance']+=codes[txt]; save("users.json", users); await update.message.reply_text(f"✅ Redeemed ${codes[txt]}!", reply_markup=user_kb())
        else: await update.message.reply_text("❌ Invalid code!", reply_markup=user_kb())
        context.user_data['wait']=None; return

    if wait=="search":
        prods=load("products.json"); res=[(k,v) for k,v in prods.items() if txt.lower() in v['brand'].lower() and not v.get('sold')]
        if not res: await update.message.reply_text("❌ No match!", reply_markup=user_kb())
        else:
            t=f"🔍 '{txt}':\n"; kb=[]
            for pid,p in res[:10]: t+=f"{p['brand']} {p['amount']} ${p['sell_price']} [{p.get('category','')}]\n"; kb.append([InlineKeyboardButton(f"{p['brand']} ${p['sell_price']}", callback_data=f"view_{pid}")])
            kb.append([InlineKeyboardButton("⬅️ Back", callback_data="uview")]); await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb))
        context.user_data['wait']=None; return

    if uid!=ADMIN_ID: return
    if wait=="add":
        try: parts=txt.split(); brand=parts[0]; amount=parts[1]; code=" ".join(parts[2:]); prods=load("products.json"); pid=str(uuid.uuid4())[:6]; c=cfg()
        except: await update.message.reply_text("Format: BRAND AMOUNT CODE"); return
        try: price=float(''.join(filter(str.isdigit, amount))) * c['perc']/100
        except: price=5
        prods[pid]={"brand":brand,"amount":amount,"code":code,"sell_price":round(price,2),"sold":False,"category":"Other"}; save("products.json", prods)
        await update.message.reply_text(f"✅ Added {brand} {amount} ${round(price,2)}", reply_markup=admin_kb()); context.user_data['wait']=None
    elif wait=="perc": try: c=cfg(); c['perc']=float(txt); save("config.json", c); await update.message.reply_text(f"✅ {c['perc']}%", reply_markup=admin_kb()); context.user_data['wait']=None
        except: await update.message.reply_text("Ex: 65")
    elif wait=="addbal":
        try: uid2, amt = txt.split(); amt=float(amt); users=load("users.json")
        except: await update.message.reply_text("USERID AMOUNT"); return
        if uid2 not in users: users[uid2]={"balance":0,"is_vendor":False,"referrals":0,"daily":None,"total_buy":0}
        users[uid2]['balance']+=amt; save("users.json", users); await update.message.reply_text(f"✅ ${amt} to {uid2}", reply_markup=admin_kb()); context.user_data['wait']=None

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=q.from_user.id; c=cfg()

    if d.startswith("listings_"):
        cat=d.replace("listings_",""); prods=load("products.json")
        active=[(k,v) for k,v in prods.items() if not v.get('sold')] if cat=="All" else [(k,v) for k,v in prods.items() if not v.get('sold') and v.get('category')==cat]
        if not active: await q.edit_message_text(f"❌ No stock in {cat}", reply_markup=filter_kb()); return
        txt=f"🔥 {cat} ({len(active)}):\n"; kb=[]
        for pid,p in active[-10:][::-1]: txt+=f"{p['brand']} {p['amount']} ${p['sell_price']} [{p.get('category','')}]\n"; kb.append([InlineKeyboardButton(f"{p['brand']} {p['amount']} ${p['sell_price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("🎯 Filter", callback_data="filter"), InlineKeyboardButton("💲 Low-High", callback_data="sort")]); kb.append([InlineKeyboardButton("⬅️ Back", callback_data="uview")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d=="filter": await q.edit_message_text("🎯 Filter:", reply_markup=filter_kb())
    elif d.startswith("view_"):
        pid=d.replace("view_",""); prods=load("products.json")
        if pid not in prods or prods[pid].get('sold'): await q.edit_message_text("❌ Sold!", reply_markup=user_kb()); return
        p=prods[pid]; txt=f"🎁 {p['brand']}\n💵 {p['amount']}\n💲 ${p['sell_price']}\n📂 {p.get('category','Other')}\nID: {pid[:6]}\n⭐ Warranty 24h\n🧾 TXT+PDF\n\nBuy?"
        kb=[[InlineKeyboardButton(f"✅ Place Order ${p['sell_price']}", callback_data=f"buy_{pid}")],[InlineKeyboardButton("⬅️ Back", callback_data="listings_All")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("buy_"):
        pid=d.replace("buy_",""); prods=load("products.json")
        if pid not in prods or prods[pid].get('sold'): await q.edit_message_text("❌ Sold!", reply_markup=user_kb()); return
        orders=load("orders.json"); oid=str(uuid.uuid4())[:6]
        orders[oid]={"buyer_id":uid,"buyer":q.from_user.first_name,"product_id":pid,"brand":prods[pid]['brand'],"amount":prods[pid]['amount'],"code":prods[pid]['code'],"sell_price":prods[pid]['sell_price'],"category":prods[pid].get('category','Other'),"status":"wait","id":oid}
        save("orders.json", orders); context.user_data['wait']=f"act_{oid}"
        await q.edit_message_text(f"✅ Order {oid}\nSubmit:\nID: yourID Pass: yourPass TRX: tx\nEx: ID:123 Pass:abc TRX:tx123", reply_markup=user_kb())
    elif d=="sort":
        prods=load("products.json"); active=sorted([(k,v) for k,v in prods.items() if not v.get('sold')], key=lambda x: x[1]['sell_price'])
        txt="💲 Low-High:\n"; kb=[]
        for pid,p in active[:10]: txt+=f"{p['brand']} {p['amount']} ${p['sell_price']} [{p.get('category','')}]\n"; kb.append([InlineKeyboardButton(f"{p['brand']} ${p['sell_price']}", callback_data=f"view_{pid}")])
        kb.append([InlineKeyboardButton("🎯 Filter", callback_data="filter")]); await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif d=="search": context.user_data['wait']='search'; await q.edit_message_text("🔍 Send brand name:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="uview")]]))
    elif d=="dep": await q.edit_message_text("💵 Deposit:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🪙 LTC", callback_data="dep_ltc"), InlineKeyboardButton("💜 SOL", callback_data="dep_sol")],[InlineKeyboardButton("⬅️ Back", callback_data="uview")]]))
    elif d=="dep_ltc":
        addr=c.get('ltc', LTC_ADDR); qr=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={addr}"
        await q.edit_message_text(f"🪙 LTC\n`{addr}`\nMin $5", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Submit TRX", callback_data="sub_ltc")],[InlineKeyboardButton("❌ Cancel", callback_data="dep")]]))
        try: await context.bot.send_photo(chat_id=uid, photo=qr)
        except: pass
    elif d=="dep_sol":
        addr=c.get('sol', SOL_ADDR); qr=f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={addr}"
        await q.edit_message_text(f"💜 SOL\n`{addr}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Submit TRX", callback_data="sub_sol")],[InlineKeyboardButton("❌ Cancel", callback_data="dep")]]))
        try: await context.bot.send_photo(chat_id=uid, photo=qr)
        except: pass
    elif d=="sub_ltc": context.user_data['wait']='trx_LTC'; await q.edit_message_text("Send LTC TRX ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="dep")]]))
    elif d=="sub_sol": context.user_data['wait']='trx_SOL'; await q.edit_message_text("Send SOL TRX ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="dep")]]))
    elif d=="bal": users=load("users.json"); await q.edit_message_text(f"💰 Balance: ${users.get(str(uid),{}).get('balance',0)}", reply_markup=user_kb())
    elif d=="prof": users=load("users.json"); u=users.get(str(uid),{}); await q.edit_message_text(f"👤 {q.from_user.first_name}\n🆔 {uid}\n💰 ${u.get('balance',0)}\n🔗 {u.get('referrals',0)} referrals", reply_markup=user_kb())
    elif d=="ai": await q.edit_message_text("🤖 AI All Language!\nType anything or /ai question\nBangla/English/Hindi", reply_markup=user_kb())
    elif d=="daily":
        users=load("users.json"); today=str(date.today())
        if users[str(uid)].get('daily')==today: await q.edit_message_text("❌ Already claimed!", reply_markup=user_kb())
        else: users[str(uid)]['balance']+=0.2; users[str(uid)]['daily']=today; save("users.json", users); await q.edit_message_text("🎁 $0.20 Daily Bonus!", reply_markup=user_kb())
    elif d=="ref": await q.edit_message_text(f"🔗 Referral:\nhttps://t.me/{context.bot.username}?start={uid}\nInvite = $1", reply_markup=user_kb())
    elif d=="lead":
        users=load("users.json"); top=sorted(users.items(), key=lambda x: x[1].get('total_buy',0), reverse=True)[:5]
        txt="🏆 Leaderboard:\n"
        for i,(uid_,u) in enumerate(top,1): txt+=f"{i}. {uid_} - {u.get('total_buy',0)} buys\n"
        await q.edit_message_text(txt, reply_markup=user_kb())
    elif d=="hist": orders=load("orders.json"); txt="📜 History:\n";
    for oid,o in orders.items():
        if str(o['buyer_id'])==str(uid): txt+=f"{oid} {o['brand']} {o['status']} TRX:{o.get('trx','')[:6]}\n"
    await q.edit_message_text(txt or "No history", reply_markup=user_kb())
    elif d=="help": await q.edit_message_text("🆘 MEGA ALL FEATURES\nFilter Free Fire/COD 880 CP, Search, Sort, Deposit QR+TRX+Cancel, ID+Pass+TRX, TXT auto + PDF manual, Vendor, Transfer, Redeem, Daily, Referral, Leaderboard, Edit Stock 1 click!", reply_markup=user_kb())
    elif d=="trans": context.user_data['wait']='trans'; await q.edit_message_text("🔄 Transfer: USERID AMOUNT\nEx: 123 5", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="uview")]]))
    elif d=="redeem": context.user_data['wait']='redeem'; await q.edit_message_text("🎁 Redeem code:\nEx: FREE5", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="uview")]]))
    elif d=="uview": await q.edit_message_text(f"🎉 
