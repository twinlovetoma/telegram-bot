import os, json, hashlib, re, time, threading, io, uuid, asyncio
from flask import Flask
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

try:
    import qrcode
except:
    qrcode = None

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_RAW = os.getenv("STOCK_CHANNEL")
CHANNEL = None
if CHANNEL_RAW:
    try:
        s = CHANNEL_RAW.strip()
        CHANNEL = int(s) if s.lstrip("-").isdigit() or s.startswith("-100") else s
    except: CHANNEL = CHANNEL_RAW.strip()

COMMISSION = 5
SELLER_PRICE = 20.0
SOL_PRICE = 150.0
LTC_PRICE = 48.88
MIN_SOL = 0.1
MIN_LTC = 0.05

def load(f):
    try:
        with open(f,"r") as fp: return json.load(fp)
    except: return {} if any(x in f for x in ["deposit","pending","users","products","settings","sold","refund","purchases","scheduled"]) else [] if "sales" in f else {}
def save(f,d):
    with open(f,"w") as fp: json.dump(d, fp, indent=2)

def get_user(uid, users):
    if uid not in users:
        users[uid] = {"balance":0.0, "sol":0.0, "ltc":0.0, "is_seller":False, "seller_lifetime":False, "name":"User", "username":"N/A", "invited":0, "referred_by":"N/A", "spent":0.0, "purchases":0}
    for k in ["sol","ltc","balance","is_seller","seller_lifetime","name","username","invited","referred_by","spent","purchases"]:
        if k not in users[uid]:
            if k in ["is_seller","seller_lifetime"]: users[uid][k]=False
            elif k in ["invited","purchases"]: users[uid][k]=0
            elif k in ["spent","balance","sol","ltc"]: users[uid][k]=0.0
            else: users[uid][k]="N/A"
    return users[uid]

def balance_text(user):
    sol_usd = user.get("sol",0)*SOL_PRICE
    ltc_usd = user.get("ltc",0)*LTC_PRICE
    total = user.get("balance",0) + sol_usd + ltc_usd
    if user.get("sol",0)==0 and user.get("ltc",0)==0: total = user.get("balance",0)
    return f"💰 *Balance:*\n💵 USD: *${total:.2f}*", total

def make_qr(address):
    if not qrcode or not address or "Not Set" in address: return None
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(address); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO(); img.save(bio, 'PNG'); bio.seek(0); return bio

def main_menu_simple():
    return [[InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],[InlineKeyboardButton("💰 My Balance", callback_data="bal")],[InlineKeyboardButton("💵 Deposit", callback_data="dep")],[InlineKeyboardButton("👤 My Profile", callback_data="prof")],[InlineKeyboardButton("👑 Admin Panel", callback_data="admin")]]

def shop_bottom_bar():
    return [[InlineKeyboardButton("⚙️ Filters", callback_data="filters"), InlineKeyboardButton("🏠 Main Menu", callback_data="back")],[InlineKeyboardButton("💰 Deposit", callback_data="dep"), InlineKeyboardButton("🔄 Refresh", callback_data="browse")]]

def purchase_detail_text(purchase):
    return f"🎭 *PSB Auto-Buy — Purchase Complete*\n━━━━━━━━━━━━━━━━━━━━━━\n\nCard Details:\n`{purchase.get('code','')}`\nBalance: ${purchase.get('amount',0)} USD\nPurchase Time: {purchase.get('purchase_time','')}\nProvider: {purchase.get('seller','')}\nPurchase ID: #{purchase.get('pid','')}\n\n⚠️ Do not check balance elsewhere.\nUse card instantly, we only refund if balance stolen within 15min."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json"); uid=str(update.effective_user.id); name = update.effective_user.first_name or "User"; username = f"@{update.effective_user.username}" if update.effective_user.username else "N/A"
    user=get_user(uid, users); user["name"]=name; user["username"]=username; save("users.json",users)
    await update.message.reply_text(f"🎉 Welcome {name}!\n\n👋 Gift Code Store", reply_markup=InlineKeyboardMarkup(main_menu_simple()))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=str(q.from_user.id)
    users=load("users.json"); products=load("products.json"); settings=load("settings.json"); purchases=load("purchases.json")
    if not settings: settings={"perc":65, "comm":5}
    if not purchases: purchases={}
    user=get_user(uid, users); save("users.json",users)
    is_admin=q.from_user.id==ADMIN; is_seller=user.get("is_seller", False)

    if d=="browse" or d.startswith("filter_"):
        if d.startswith("filter_"): context.user_data['filter'] = d
        user_filter = context.user_data.get('filter', 'filter_all'); all_products = list(products.items())
        if not all_products:
            await q.edit_message_text("😔 *No Stock Available*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]])); return
        filtered = all_products
        if user_filter == "filter_low": filtered = sorted(all_products, key=lambda x: x[1]['sell_price'])
        elif user_filter == "filter_high": filtered = sorted(all_products, key=lambda x: x[1]['sell_price'], reverse=True)
        elif user_filter == "filter_under5": filtered = [x for x in all_products if x[1]['sell_price'] < 5]
        elif user_filter == "filter_5_10": filtered = [x for x in all_products if 5 <= x[1]['sell_price'] <= 10]
        elif user_filter == "filter_above10": filtered = [x for x in all_products if x[1]['sell_price'] > 10]
        txt=f"🔥 *Latest Listings* 🔥\n📦 Total: *{len(filtered)}*\n\n"; kb=[]
        for pid,p in filtered[:15]: kb.append([InlineKeyboardButton(f"🛒 {p.get('first4')}**** - ${p['sell_price']}", callback_data=f"buy_{pid}")])
        kb.extend(shop_bottom_bar()); await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)); return
    elif d=="filters":
        kb=[[InlineKeyboardButton("💲 Low-High", callback_data="filter_low"), InlineKeyboardButton("High-Low", callback_data="filter_high")],[InlineKeyboardButton("Under $5", callback_data="filter_under5"), InlineKeyboardButton("$5-$10", callback_data="filter_5_10")],[InlineKeyboardButton("Above $10", callback_data="filter_above10"), InlineKeyboardButton("All", callback_data="filter_all")],[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]]
        await q.edit_message_text("⚙️ *FILTERS*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)); return
    elif d=="back" or d=="back_to_menu":
        await q.edit_message_text(f"🎉 Welcome {user.get('name','User')}!\n\n👋 Gift Code Store", reply_markup=InlineKeyboardMarkup(main_menu_simple())); return
    elif d=="bal":
        bal_txt,_=balance_text(user); await q.edit_message_text(bal_txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Deposit", callback_data="dep")],[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]])); return
    elif d=="dep":
        bal_txt,_=balance_text(user); await q.edit_message_text(f"💵 *Deposit*\n{bal_txt}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🟣 SOL", callback_data="dep_sol"), InlineKeyboardButton("🔵 LTC", callback_data="dep_ltc")],[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]])); return
    elif d in ["dep_sol","dep_ltc"]:
        coin="SOL" if d=="dep_sol" else "LTC"; min_amt=MIN_SOL if coin=="SOL" else MIN_LTC; addr=settings.get("sol_deposit" if coin=="SOL" else "ltc_deposit","Not Set")
        if "Not Set" in addr: await q.edit_message_text(f"❌ {coin} Not Set", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="dep")]])); return
        dep_reqs=load("deposit_requests.json"); req_id=hashlib.md5(f"{uid}{coin}{time.time()}".encode()).hexdigest()[:6]; expire_at=datetime.now()+timedelta(minutes=30)
        dep_reqs[req_id]={"uid":uid,"coin":coin,"addr":addr,"min":min_amt,"expire":expire_at.strftime("%Y-%m-%d %H:%M:%S"),"txid":None}; save("deposit_requests.json",dep_reqs)
        txt=f"{'🟣' if coin=='SOL' else '🔵'} *{coin} DEPOSIT*\n🆔 `#{req_id}`\n📥 `{addr}`\n💰 Min: `{min_amt}`\n"; kb=[[InlineKeyboardButton(f"📝 Submit TXID", callback_data=f"submit_txid_{req_id}")],[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]]
        qr_bio=make_qr(addr)
        if qr_bio:
            try: await q.message.delete()
            except: pass
            await context.bot.send_photo(chat_id=q.message.chat_id, photo=qr_bio, caption=txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        else: await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return
    elif d.startswith("submit_txid_"):
        context.user_data['w']=f'txid_{d.split("submit_txid_")[1]}'; await q.edit_message_text(f"📝 Send TXID for #{d.split('submit_txid_')[1]}"); return

    elif d=="prof" or d=="refresh_prof":
        sales=load("sales.json");
        if not isinstance(sales, list): sales=[]
        my_sales=[s for s in sales if str(s.get('buyer'))==uid]; count=len(my_sales); spent=sum([float(s.get('price',0)) for s in my_sales]); user["purchases"]=count; user["spent"]=spent; save("users.json",users)
        _, total=balance_text(user)
        txt=(f"👤 {user.get('name','Mohammed sayem')}\n🧠 \"I know that I know nothing.\"\n💬 By: Socrates\n\n🆔 User ID: {uid}\n@ Username: {user.get('username','@twinlovetoma')}\n\n💵 USD Total: ${total:.2f}\n\n🛒 Purchases\n• Count: {count}\n• USD Spent: ${spent:.2f}\n\n👥 Referrals\n• Invited: {user.get('invited',0)}\n• Referred By: {user.get('referred_by','N/A')}\n\n🛠️ Access\n• Seller: {'✅' if is_seller or is_admin else '❌'}\n• Re-Sell: ⏳ Coming Soon\n\n_Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        kb=[[InlineKeyboardButton("🏪 Vendor Dashboard", callback_data="seller_dash")],[InlineKeyboardButton("🔄 Transfer", callback_data="transfer"), InlineKeyboardButton("📤 Withdraw", callback_data="withdraw"), InlineKeyboardButton("🎁 Redeem Co", callback_data="redeem")],[InlineKeyboardButton("💳 Deposit", callback_data="dep"), InlineKeyboardButton("📜 Cards History", callback_data="my_trans")],[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_prof"), InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_menu")]]
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)); return

    elif d=="seller_dash" or d=="buy_seller_access":
        if d=="buy_seller_access":
            if is_seller or is_admin: await q.edit_message_text("✅ Already Lifetime!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Open Dashboard", callback_data="seller_dash")]])); return
            _, total=balance_text(user)
            if total < SELLER_PRICE: await q.edit_message_text(f"❌ *You don't have enough balance!*\nNeed: ${SELLER_PRICE}\nYour: ${total:.2f}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Deposit", callback_data="dep")],[InlineKeyboardButton("Back", callback_data="back_to_menu")]])); return
            else:
                if user.get("balance",0)>=SELLER_PRICE: user["balance"]-=SELLER_PRICE
                else:
                    rem=SELLER_PRICE-user.get("balance",0); user["balance"]=0
                    if user.get("ltc",0)*LTC_PRICE>=rem: user["ltc"]-=rem/LTC_PRICE
                    else: rem-=user.get("ltc",0)*LTC_PRICE; user["ltc"]=0; user["sol"]-=rem/SOL_PRICE
                user["is_seller"]=True; user["seller_lifetime"]=True; save("users.json",users)
                await q.edit_message_text(f"🎉 *Vendor Access Purchased - Lifetime!* ✅\nPaid ${SELLER_PRICE}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏪 Open Dashboard", callback_data="seller_dash")]])); return
        if not is_seller and not is_admin:
            _, total=balance_text(user)
            await q.edit_message_text(f"🔒 *Vendor Access Required*\nPrice: *${SELLER_PRICE} Lifetime*\nYour: ${total:.2f}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"💸 Buy - ${SELLER_PRICE}", callback_data="buy_seller_access")],[InlineKeyboardButton("Deposit", callback_data="dep")]])); return
        my_products={pid:p for pid,p in products.items() if p.get("seller_id")==uid}; bal_txt,_=balance_text(user)
        await q.edit_message_text(f"🏪 *Vendor Dashboard Lifetime* ✅\n{bal_txt}\n📦 AVL: {len(my_products)}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add", callback_data="add")],[InlineKeyboardButton("📦 AVL", callback_data="my_listings")],[InlineKeyboardButton("📊 My Sales", callback_data="my_sales")],[InlineKeyboardButton("Back", callback_data="back_to_menu")]])); return

    elif d in ["my_listings","remove_list","my_sales","add","setp","ab","relist","vendors","allsellers","pending","sales","buyers","set_deposit","set_sol_addr","set_ltc_addr","dep_reqs","refund_reqs","list_del","transfer","withdraw","redeem","my_trans"]:
        # keep existing logic short - full handlers as before
        if d=="my_listings":
            my_products={pid:p for pid,p in products.items() if p.get("seller_id")==uid}
            if not my_products: await q.edit_message_text("No AVL", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="seller_dash")]])); return
            txt="📦 AVL\n"; kb=[]
            for pid,p in list(my_products.items())[:15]: txt+=f"{p.get('first4')}**** ${p['sell_price']}\n"; kb.append([InlineKeyboardButton(f"❌ {p.get('first4')}", callback_data=f"seller_del_{pid}")])
            kb.append([InlineKeyboardButton("Back", callback_data="seller_dash")]); await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return
        elif d=="my_sales":
            sales=load("sales.json");
            if not isinstance(sales, list): sales=[]
            my_sales=[s for s in sales if s.get("seller")==uid]
            if not my_sales: await q.edit_message_text("No sales", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="seller_dash")]])); return
            txt="📊 Sales (15min delayed)\n"
            for s in my_sales[-10:]: txt+=f"{s['time']} {s['first4']} ${s['price']} -> ${s.get('seller_earn',0)} [{s.get('payout_status','paid')}]\n"
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="seller_dash")]])); return
        elif d=="add": context.user_data['w']='add'; await q.edit_message_text("📤 Send CODE $AMT per line"); return
        elif d=="setp": context.user_data['w']='perc'; await q.edit_message_text("Send % ex: 65"); return
        elif d=="ab": context.user_data['w']='ab'; await q.edit_message_text("Send USERID AMOUNT ex: 123456 10"); return
        elif d=="transfer": context.user_data['w']='transfer'; await q.edit_message_text("🔄 Send USERID AMOUNT ex: 6699688350 5"); return
        elif d=="withdraw": context.user_data['w']='withdraw'; await q.edit_message_text("📤 Send AMOUNT ADDRESS"); return
        elif d=="redeem": context.user_data['w']='redeem'; await q.edit_message_text("🎁 Send Code"); return
        elif d=="my_trans":
            my_purs={k:v for k,v in purchases.items() if v.get('buyer')==uid}
            if not my_purs: await q.edit_message_text("No history", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="prof")]])); return
            txt="📜 Cards History\n"
            for pid,p in list(my_purs.items())[-10:]: txt+=f"{pid[:8]} ${p.get('price')} {p.get('purchase_time')}\n"
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="prof")]])); return
        elif d=="admin" and is_admin:
            await q.edit_message_text(f"👑 Admin\nUsers: {len(users)} Listings: {len(products)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add", callback_data="add")],[InlineKeyboardButton("📋 List/Del", callback_data="list_del")],[InlineKeyboardButton("👥 Users", callback_data="allsellers")],[InlineKeyboardButton("💸 Add Bal", callback_data="ab")],[InlineKeyboardButton("⏳ Pending", callback_data="pending")],[InlineKeyboardButton("📊 Sales", callback_data="sales")],[InlineKeyboardButton("💳 Set Addr", callback_data="set_deposit")],[InlineKeyboardButton("💰 Dep Req", callback_data="dep_reqs")],[InlineKeyboardButton("⚠️ Refund", callback_data="refund_reqs")],[InlineKeyboardButton("Back", callback_data="back")]])); return
        elif d=="list_del":
            if not products: await q.edit_message_text("No listings", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]])); return
            txt="List/Del\n"; kb=[]
            for pid,p in list(products.items())[:10]: txt+=f"{p.get('first4')} ${p['sell_price']}\n"; kb.append([InlineKeyboardButton(f"Del {p.get('first4')}", callback_data=f"del_{pid}")])
            kb.append([InlineKeyboardButton("Back", callback_data="admin")]); await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return
        elif d=="set_deposit" and is_admin:
            await q.edit_message_text(f"SOL: {settings.get('sol_deposit','Not Set')}\nLTC: {settings.get('ltc_deposit','Not Set')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Set SOL", callback_data="set_sol_addr")],[InlineKeyboardButton("Set LTC", callback_data="set_ltc_addr")],[InlineKeyboardButton("Back", callback_data="admin")]])); return
        elif d=="set_sol_addr": context.user_data['w']='set_sol_addr'; await q.edit_message_text("Send SOL addr"); return
        elif d=="set_ltc_addr": context.user_data['w']='set_ltc_addr'; await q.edit_message_text("Send LTC addr"); return
        elif d=="pending" and is_admin:
            pending=load("pending.json")
            if not pending: await q.edit_message_text("No pending", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]])); return
            txt="Pending:\n"; kb=[]
            for pend_id,ord in list(pending.items())[-5:]: txt+=f"#{pend_id} ${ord['price']}\n"; kb.append([InlineKeyboardButton(f"✅ {pend_id}", callback_data=f"apv_{pend_id}"), InlineKeyboardButton(f"❌", callback_data=f"rej_{pend_id}")])
            kb.append([InlineKeyboardButton("Back", callback_data="admin")]); await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb)); return

    elif d.startswith("del_"):
        pid=d.split("del_")[1]
        if pid in products: del products[pid]; save("products.json",products)
        await q.edit_message_text("Deleted", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]])); return
    elif d.startswith("seller_del_"):
        pid=d.split("seller_del_")[1]
        if pid in products: del products[pid]; save("products.json",products)
        await q.edit_message_text("Removed", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="seller_dash")]])); return
    elif d.startswith("apv_") and is_admin:
        pend_id=d.split("apv_")[1]; pending=load("pending.json"); products=load("products.json"); users=load("users.json")
        if pend_id not in pending: return
        ord=pending[pend_id]; pid=ord["pid"]; buyer=ord["buyer"]; seller_id=ord["seller"]; p=products.get(pid)
        if not p: del pending[pend_id]; save("pending.json",pending); return
        sell_price=float(ord["price"]); comm=round(sell_price*COMMISSION/100,2); seller_earn=round(sell_price-comm,2)
        scheduled=load("scheduled_payouts.json"); pay_time=datetime.now()+timedelta(minutes=15)
        scheduled[pend_id]={"seller":seller_id,"buyer":buyer,"price":sell_price,"seller_earn":seller_earn,"comm":comm,"first4":ord["first4"],"code":ord["code"],"pay_time":pay_time.strftime("%Y-%m-%d %H:%M:%S")}; save("scheduled_payouts.json",scheduled)
        admin_user=get_user(str(ADMIN), use
