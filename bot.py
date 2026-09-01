import os, json, hashlib, re, time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "0"))
CHANNEL = os.getenv("STOCK_CHANNEL")
COMMISSION = 5

def load(f):
    try:
        with open(f,"r") as fp: return json.load(fp)
    except: return {} if "sales" not in f else []
def save(f,d):
    with open(f,"w") as fp: json.dump(d, fp, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json")
    uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0.0,"is_seller":False}
        save("users.json",users)
    kb=[
        [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
        [InlineKeyboardButton("💰 My Balance", callback_data="bal")],
        [InlineKeyboardButton("💵 Deposit", callback_data="dep")],
        [InlineKeyboardButton("👤 My Profile", callback_data="prof")]
    ]
    if users[uid].get("is_seller") or int(uid)==ADMIN:
        kb.append([InlineKeyboardButton("➕ Add My Stock", callback_data="add")])
    await update.message.reply_text(f"🎉 Welcome {update.effective_user.first_name}!", reply_markup=InlineKeyboardMarkup(kb))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    d=q.data
    uid=str(q.from_user.id)
    users=load("users.json")
    products=load("products.json")
    settings=load("settings.json")
    if not settings: settings={"perc":65}
    if uid not in users:
        users[uid]={"balance":0.0,"is_seller":False}
        save("users.json",users)

    if d=="browse":
        if not products:
            await q.edit_message_text("No stock", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
            return
        txt="🔥 Available Stock:\n\n"
        kb=[]
        for i,(pid,p) in enumerate(list(products.items())[:20],1):
            txt+=f"{i}. {p.get('first4','CODE')}**** - ${p['sell_price']} (MRP ${p['amount']})\n"
            kb.append([InlineKeyboardButton(f"Buy {p.get('first4','CODE')}**** - ${p['sell_price']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif d=="back":
        kb=[
            [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
            [InlineKeyboardButton("💰 My Balance", callback_data="bal")],
            [InlineKeyboardButton("💵 Deposit", callback_data="dep")],
            [InlineKeyboardButton("👤 My Profile", callback_data="prof")]
        ]
        if users.get(uid,{}).get("is_seller") or q.from_user.id==ADMIN:
            kb.append([InlineKeyboardButton("➕ Add My Stock", callback_data="add")])
        await q.edit_message_text("Main Menu", reply_markup=InlineKeyboardMarkup(kb))

    elif d=="bal":
        await q.edit_message_text(f"💰 Balance: ${users.get(uid,{}).get('balance',0)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif d=="dep":
        await q.edit_message_text(f"💵 Deposit\nYour ID: {uid}\nContact admin", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif d=="prof":
        b=users.get(uid,{}).get('balance',0)
        is_s=users.get(uid,{}).get('is_seller',False)
        kb=[[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        if q.from_user.id==ADMIN:
            kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        if not is_s:
            kb.append([InlineKeyboardButton("🏪 Become Seller", callback_data="apply_vendor")])
        await q.edit_message_text(f"👤 ID: {uid}\nBal: ${b}\nSeller: {is_s}", reply_markup=InlineKeyboardMarkup(kb))

    elif d=="admin" and q.from_user.id==ADMIN:
        kb=[
            [InlineKeyboardButton("➕ Add Stock", callback_data="add"), InlineKeyboardButton("💲 Set %", callback_data="setp")],
            [InlineKeyboardButton("💵 Add Balance", callback_data="ab"), InlineKeyboardButton("🔄 Relist", callback_data="relist")],
            [InlineKeyboardButton("🏪 Vendor Req", callback_data="vendors"), InlineKeyboardButton("👥 All Sellers", callback_data="allsellers")],
            [InlineKeyboardButton("⏳ Pending Orders", callback_data="pending"), InlineKeyboardButton("📊 Sales History", callback_data="sales")],
            [InlineKeyboardButton("📜 Buyer History", callback_data="buyers")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await q.edit_message_text(f"👑 Admin Panel\nPerc: {settings.get('perc',65)}%\nComm: {COMMISSION}%\nStock: {len(products)}", reply_markup=InlineKeyboardMarkup(kb))

    elif d in ["add"]:
        if not (users.get(uid,{}).get("is_seller") or q.from_user.id==ADMIN):
            await q.edit_message_text("❌ Only sellers can add")
            return
        context.user_data['w']='add'
        await q.edit_message_text("Send codes like:\n435RG:xx:xx:xxx $3\nOne per line")

    elif d=="setp" and q.from_user.id==ADMIN:
        context.user_data['w']='perc'
        await q.edit_message_text("Send % ex: 65")

    elif d=="ab" and q.from_user.id==ADMIN:
        context.user_data['w']='ab'
        await q.edit_message_text("Send: USERID AMOUNT\nEx: 123456 10")

    elif d=="relist" and q.from_user.id==ADMIN:
        sold=load("sold.json")
        if not sold:
            await q.edit_message_text("No sold items", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        txt="🔄 Sold Items:\n\n"; kb=[]
        for pid,p in list(sold.items())[:10]:
            txt+=f"{p.get('first4')}**** - ${p['sell_price']}\n"
            kb.append([InlineKeyboardButton(f"Relist {p.get('first4')}****", callback_data=f"do_relist_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="admin")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("do_relist_") and q.from_user.id==ADMIN:
        pid=d.split("do_relist_")[1]
        sold=load("sold.json"); products=load("products.json")
        if pid in sold:
            products[pid]=sold[pid]; del sold[pid]
            save("products.json",products); save("sold.json",sold)
        await q.edit_message_text("✅ Relisted", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))

    elif d=="vendors" and q.from_user.id==ADMIN:
        req=[u for u,dat in users.items() if dat.get('vendor_req')]
        if not req:
            await q.edit_message_text("No vendor requests", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        txt="Vendor Requests:\n\n"; kb=[]
        for uid2 in req[:10]:
            txt+=f"ID: {uid2}\n"
            kb.append([InlineKeyboardButton(f"Approve {uid2}", callback_data=f"approve_{uid2}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="admin")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("approve_") and q.from_user.id==ADMIN:
        uid2=d.split("approve_")[1]
        users[uid2]["is_seller"]=True; users[uid2].pop("vendor_req",None)
        save("users.json",users)
        await q.edit_message_text(f"✅ {uid2} is seller now", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
        try: await context.bot.send_message(chat_id=int(uid2), text="✅ You are seller now!")
        except: pass

    elif d=="allsellers" and q.from_user.id==ADMIN:
        txt="👥 Sellers:\n\n"
        for uid2,dat in users.items():
            if dat.get('is_seller'):
                txt+=f"{uid2} - Bal ${dat.get('balance',0)}\n"
        if txt=="👥 Sellers:\n\n": txt="No sellers yet"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))

    elif d=="pending" and q.from_user.id==ADMIN:
        pending=load("pending.json")
        if not pending:
            await q.edit_message_text("No pending orders", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        txt="⏳ PENDING ORDERS:\n\n"; kb=[]
        for pend_id,ord in list(pending.items())[-10:]:
            txt+=f"#{pend_id} Buyer:{ord['buyer']} {ord['first4']}**** ${ord['price']} {ord['time']}\n"
            kb.append([InlineKeyboardButton(f"✅ Approve {pend_id}", callback_data=f"apv_{pend_id}"), InlineKeyboardButton(f"❌ Reject", callback_data=f"rej_{pend_id}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="admin")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("apv_") and q.from_user.id==ADMIN:
        pend_id=d.split("apv_")[1]
        pending=load("pending.json"); products=load("products.json"); users=load("users.json")
        if pend_id not in pending:
            await q.edit_message_text("Already processed", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        ord=pending[pend_id]
        pid=ord["pid"]; buyer=ord["buyer"]; seller_id=ord["seller"]
        p=products.get(pid)
        if not p:
            del pending[pend_id]; save("pending.json",pending)
            await q.edit_message_text("Item already sold", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        sell_price=float(ord["price"]); comm=round(sell_price*COMMISSION/100,2); seller_earn=round(sell_price-comm,2)
        if seller_id not in users: users[seller_id]={"balance":0,"is_seller":True}
        if str(seller_id)!=str(ADMIN):
            users[seller_id]["balance"]=users[seller_id].get("balance",0)+seller_earn
            users[str(ADMIN)]["balance"]=users[str(ADMIN)].get("balance",0)+comm
        else:
            users[str(ADMIN)]["balance"]=users[str(ADMIN)].get("balance",0)+sell_price
        save("users.json",users)
        sales=load("sales.json")
        if not isinstance(sales, list): sales=[]
        sales.append({"time":time.strftime("%d-%m %H:%M"), "code":ord["code"], "first4":ord["first4"], "price":sell_price, "seller":seller_id, "buyer":buyer, "seller_earn":seller_earn, "comm":comm if str(seller_id)!=str(ADMIN) else sell_price})
        save("sales.json",sales)
        sold=load("sold.json"); sold[pid]=p; save("sold.json",sold)
        code=ord["code"]; del products[pid]; save("products.json",products)
        del pending[pend_id]; save("pending.json",pending)
        await q.edit_message_text(f"✅ Approved #{pend_id}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
        try:
            refund_text = f"✅ APPROVED!\n\nYour Code:\n`{code}`\n\n━━━━━━━━━━━━━━\n📜 REFUND POLICY\n━━━━━━━━━━━━━━\n❌ No refund after code view\n✅ Refund if code invalid / already used (proof within 30min)\n⚠️ Wrong region = no refund\n📩 Issue? Contact Admin\n━━━━━━━━━━━━━━"
            await context.bot.send_message(chat_id=int(buyer), text=refund_text, parse_mode="Markdown")
        except: pass

    elif d.startswith("rej_") and q.from_user.id==ADMIN:
        pend_id=d.split("rej_")[1]
        pending=load("pending.json"); users=load("users.json")
        if pend_id not in pending: return
        ord=pending[pend_id]; buyer=ord["buyer"]; price=float(ord["price"])
        users[buyer]["balance"]=users[buyer].get("balance",0)+price
        save("users.json",users)
        del pending[pend_id]; save("pending.json",pending)
        await q.edit_message_text(f"❌ Rejected #{pend_id} - Refunded ${price}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
        try: await context.bot.send_message(chat_id=int(buyer), text=f"❌ Order #{pend_id} rejected. ${price} refunded.")
        except: pass

    elif d=="sales" and q.from_user.id==ADMIN:
        sales=load("sales.json")
        if not sales:
            await q.edit_message_text("No sales yet", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        txt="📊 SALES (Last 15):\n\n"
        for s in sales[-15:][::-1]:
            txt+=f"🕒 {s['time']}\nSeller:{s['seller']} -> Buyer:{s['buyer']}\n{s['first4']}**** ${s['price']} | Seller ${s['seller_earn']} You ${s['comm']}\n---\n"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))

    elif d=="buyers" and q.from_user.id==ADMIN:
        sales=load("sales.json")
        if not sales:
            await q.edit_message_text("No buyers", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))
            return
        buyers={}
        for s in sales: buyers[s['buyer']]=buyers.get(s['buyer'],0)+1
        txt="📜 BUYERS:\n\n"
        for b,c in buyers.items(): txt+=f"{b}: {c} items\n"
        txt+="\nRecent:\n"
        for s in sales[-10:][::-1]: txt+=f"{s['buyer']} bought {s['first4']}**** ${s['price']}\n"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin")]]))

    elif d=="apply_vendor":
        users[uid]["vendor_req"]=True; save("users.json",users)
        await q.edit_message_text("✅ Request sent to admin", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        try: await context.bot.send_message(chat_id=ADMIN, text=f"🏪 Vendor req: {uid}")
        except: pass

    elif d.startswith("buy_"):
        pid=d.split("buy_")[1]
        p=products.get(pid)
        if not p:
            await q.edit_message_text("❌ Sold out", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="browse")]]))
            return
        if users[uid]["balance"] < float(p["sell_price"]):
            await q.edit_message_text(f"❌ Low bal Need ${p['sell_price']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
            return
        pending=load("pending.json")
        pend_id=hashlib.md5(f"{uid}{pid}{time.time()}".encode()).hexdigest()[:6]
        pending[pend_id]={"pid":pid, "buyer":uid, "seller":p.get("seller_id",str(ADMIN)), "price":p["sell_price"], "first4":p.get("first4"), "code":p["code"], "time":time.strftime("%d-%m %H:%M")}
        save("pending.json",pending)
        users[uid]["balance"]-=float(p["sell_price"])
        save("users.json",users)
        await q.edit_message_text(f"⏳ Request Sent #{pend_id}\nItem: {p.get('first4')}**** - ${p['sell_price']}\nWaiting for admin approval", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
        try:
            kb_admin=[[InlineKeyboardButton(f"✅ Approve {pend_id}", callback_data=f"apv_{pend_id}"), InlineKeyboardButton(f"❌ Reject", callback_data=f"rej_{pend_id}")]]
            await context.bot.send_message(chat_id=ADMIN, text=f"🔔 NEW ORDER #{pend_id}\nBuyer: {uid}\nItem: {p.get('first4')}**** - ${p['sell_price']}\nSeller: {p.get('seller_id')}", reply_markup=InlineKeyboardMarkup(kb_admin))
        except: pass

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    w=context.user_data.get('w')
    if not w: return
    if w=='add':
        products=load("products.json"); settings=load("settings.json")
        if not settings: settings={"perc":65}
        perc=settings.get("perc",65)
        cnt=0; uid=str(update.effective_user.id)
        for line in txt.split('\n'):
            if '$' not in line: continue
            try:
                m=re.search(r'\$\s*(\d+(?:\.\d+)?)', line)
                if not m: continue
                amt=float(m.group(1))
                full_code=line.split('$')[0].strip()
                if len(full_code)<4: continue
                pid=hashlib.md5(f"{full_code}{time.time()}{cnt}".encode()).hexdigest()[:8]
                sell=round(amt*perc/100,2)
                first4=full_code[:4]
                products[pid]={"first4":first4, "code":full_code, "amount":amt,"sell_price":sell, "seller_id":uid}
                cnt+=1
                if CHANNEL:
                    try: await context.bot.send_message(chat_id=CHANNEL, text=f"🆕 NEW STOCK\n{first4}**** - ${sell} (MRP ${amt})")
                    except: pass
            except: pass
        save("products.json",products)
        await update.message.reply_text(f"✅ {cnt} added - You get 95%")
        context.user_data['w']=None
    elif w=='perc':
        try:
            p=float(txt.replace('%','').strip())
            save("settings.json",{"perc":p})
            products=load("products.json")
            for k in products: products[k]["sell_price"]=round(float(products[k]["amount"])*p/100,2)
            save("products.json",products)
            await update.message.reply_text(f"✅ {p}% set")
        except: pass
        context.user_data['w']=None
    elif w=='ab':
        try:
            uid2,amt=txt.split(); amt=float(amt)
            users=load("users.json")
            if uid2 not in users: users[uid2]={"balance":0,"is_seller":False}
            users[uid2]["balance"]=users[uid2].get("balance",0)+amt
            save("users.json",users)
            await update.message.reply_text(f"✅ ${amt} to {uid2}")
        except:
            await update.message.reply_text("Format: USERID AMOUNT")
        context.user_data['w']=None

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mh))
    app.run_polling()

if __name__=="__main__":
    main()
