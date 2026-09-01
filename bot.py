import os, json, threading, hashlib, re, requests, random
from datetime import datetime
from io import BytesIO
import qrcode
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL = os.getenv("STOCK_CHANNEL_ID", "")
SOL_ADDR = os.getenv("SOL_ADDRESS", "Not set")
LTC_ADDR = os.getenv("LTC_ADDRESS", "Not set")

SELLER_FEE = 20.0
RELIST_FEE = 10.0
RESALE_SHARE = 0.35
ADMIN_CUT = 0.04

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Gift Store OK"
threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

def load(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,'r',encoding='utf-8') as x: return json.load(x)
    except: return {}
def save(f,d):
    with open(f,'w',encoding='utf-8') as x: json.dump(d,x,indent=2)

def make_qr(text):
    qr=qrcode.QRCode(box_size=10, border=2); qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white"); bio=BytesIO(); img.save(bio,'PNG'); bio.seek(0); return bio

def get_prices():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana,litecoin&vs_currencies=usd", timeout=5).json()
        return float(r['solana']['usd']), float(r['litecoin']['usd'])
    except: return 0.0,0.0

def parse_gift(text):
    m=re.search(r'\$\s*(\d+(?:\.\d+)?)', text)
    if not m: raise ValueError("Format: BRAND CODE $AMOUNT ex: STEAM ABCD123 $25")
    amount=float(m.group(1))
    before=text.split('$')[0].strip()
    parts=before.split()
    if not parts: raise ValueError("Brand dao")
    brand=parts[0].upper()
    code=' '.join(parts[1:]) if len(parts)>1 else before
    if len(code)<3: raise ValueError("Code too short")
    h=hashlib.sha256(code.lower().strip().encode()).hexdigest()
    return brand, code.strip(), amount, h

def get_main_menu(uid_int):
    kb=[
        [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")]
    ]
    if uid_int==ADMIN: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

async def set_commands(app):
    cmds=[BotCommand("start","Launch bot"),BotCommand("profile","View profile"),BotCommand("balance","View balance"),BotCommand("deposit","Deposit"),BotCommand("listings","Browse")]
    await app.bot.set_my_commands(cmds)

async def send_stock(context, p):
    if not STOCK_CHANNEL: return
    try:
        await context.bot.send_message(chat_id=STOCK_CHANNEL, text=f"🔥 NEW LISTING\n🎁 {p['brand']} ${p['amount']} -> ${p['sell_price']}\nSeller: {p.get('seller_id')}\nTotal: {len(load('products.json'))}")
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json"); uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0,"sol":0,"ltc":0,"username":update.effective_user.username,"first_name":update.effective_user.first_name,"joined":datetime.now().strftime("%Y-%m-%d %H:%M"),"purchases":0,"spent":0,"is_seller":False,"can_resell":False,"invited":0,"referred_by":"N/A"}
        save("users.json",users)
    await update.message.reply_text(f"🎉 Welcome {update.effective_user.first_name}!\n\n👋 Gift Code Store", reply_markup=get_main_menu(update.effective_user.id))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    users=load("users.json"); products=load("products.json"); history=load("history.json")
    uid=str(q.from_user.id); uid_int=q.from_user.id
    sol_p, ltc_p = get_prices()

    if q.data=="browse":
        if not products: await q.edit_message_text("No listings", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])); return
        ub=users.get(uid,{"balance":0,"sol":0,"ltc":0}); total=ub.get("balance",0)+ub.get("sol",0)*sol_p+ub.get("ltc",0)*ltc_p
        t=f"💵 Your USD Total: ${total:.2f} | SOL ${sol_p} | LTC ${ltc_p}\n\n🔥 Latest:\n"
        kb=[]
        for pid,p in list(products.items())[-30:][::-1]:
            t+=f"{p['brand']} ${p['amount']} -> ${p['sell_price']}\n"
            kb.append([InlineKeyboardButton(f"Buy {p['brand']} ${p['sell_price']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("buy_"):
        pid=q.data.split("_",1)[1]; p=products.get(pid)
        if not p: await q.edit_message_text("Sold"); return
        await q.edit_message_text(f"🎁 {p['brand']}\nAmount: ${p['amount']}\nPrice: ${p['sell_price']}\nSeller: {p.get('seller_id')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Confirm ${p['sell_price']}", callback_data=f"confirm_{pid}")],[InlineKeyboardButton("Back", callback_data="browse")]]))

    elif q.data.startswith("confirm_"):
        pid=q.data.split("_",1)[1]; p=products.get(pid)
        if not p: return
        price=float(p['sell_price']); ub=users.get(uid,{}); bal=ub.get("balance",0)
        if bal<price: await q.edit_message_text(f"Low bal Need ${price} have ${bal}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")]])); return
        users[uid]["balance"]=bal-price
        if p.get("is_resale") and p.get("original_buyer") in users:
            users[p["original_buyer"]]["balance"]=users[p["original_buyer"]].get("balance",0)+price*RESALE_SHARE
            if str(ADMIN) in users: users[str(ADMIN)]["balance"]=users[str(ADMIN)].get("balance",0)+price*ADMIN_CUT
        users[uid]["purchases"]=users[uid].get("purchases",0)+1; users[uid]["spent"]=users[uid].get("spent",0)+price; save("users.json",users)
        if uid not in history: history[uid]=[]
        history[uid].append({"brand":p['brand'],"amount":p['amount'],"price":price,"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"code":p['code']}); save("history.json",history)
        try: await context.bot.send_message(chat_id=ADMIN, text=f"✅ PURCHASE\nBuyer {uid} @{q.from_user.username}\n{p['brand']} ${p['amount']} -> ${price}\nCode: {p['code']}")
        except: pass
        del products[pid]; save("products.json",products)
        await q.edit_message_text(f"✅ Bought!\nCode: `{p['code']}`\nSave it now.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Resell", callback_data=f"resell_{p['brand']}_{p['code']}_{p['amount']}")],[InlineKeyboardButton("History", callback_data="history")],[InlineKeyboardButton("Back", callback_data="back")]]))

    elif q.data=="back": await q.edit_message_text("Main Menu", reply_markup=get_main_menu(uid_int))
    elif q.data=="profile":
        u=users.get(uid,{}); total=u.get("balance",0)+u.get("sol",0)*sol_p+u.get("ltc",0)*ltc_p
        txt=f"👤 {q.from_user.first_name}\n🆔 {uid} @{q.from_user.username}\n\n💵 USD Total: ${total:.2f}\n💰 Bal: ${u.get('balance',0)} SOL:{u.get('sol',0)} LTC:{u.get('ltc',0)}\n\n🛒 Purchases: {u.get('purchases',0)} Spent: ${u.get('spent',0)}\n\n🛠 Access\n- Seller: {'✅' if u.get('is_seller') else '❌ $20'}\n- Re-Sell: {'✅' if u.get('can_resell') else '❌ $10'}\n\nLast: {datetime.now()}"
        kb=[[InlineKeyboardButton("🏪 Vendor Dashboard", callback_data="vendor")],[InlineKeyboardButton("🔄 Transfer", callback_data="transfer"),InlineKeyboardButton("🎁 Redeem", callback_data="redeem")],[InlineKeyboardButton("💳 Deposit", callback_data="deposit"),InlineKeyboardButton("📜 History", callback_data="history")],[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="balance":
        u=users.get(uid,{}); total=u.get("balance",0)+u.get("sol",0)*sol_p+u.get("ltc",0)*ltc_p
        await q.edit_message_text(f"💰 USD Total ${total:.2f}\nBal ${u.get('balance',0)}\nSOL {u.get('sol',0)} x ${sol_p}\nLTC {u.get('ltc',0)} x ${ltc_p}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")],[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="deposit":
        await q.edit_message_text("Select:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SOL", callback_data="dep_sol")],[InlineKeyboardButton("LTC", callback_data="dep_ltc")],[InlineKeyboardButton(f"Buy Seller ${SELLER_FEE}", callback_data="buy_seller")],[InlineKeyboardButton(f"Buy Re-sell ${RELIST_FEE}", callback_data="buy_resell")],[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="buy_seller":
        if users[uid].get("balance",0)>=SELLER_FEE: users[uid]["balance"]-=SELLER_FEE; users[uid]["is_seller"]=True; save("users.json",users); await q.edit_message_text("✅ Seller enabled")
        else: await q.edit_message_text(f"Need ${SELLER_FEE}")
    elif q.data=="buy_resell":
        if users[uid].get("balance",0)>=RELIST_FEE: users[uid]["balance"]-=RELIST_FEE; users[uid]["can_resell"]=True; save("users.json",users); await q.edit_message_text("✅ Re-sell enabled")
        else: await q.edit_message_text(f"Need ${RELIST_FEE}")
    elif q.data in ["dep_sol","dep_ltc"]:
        addr=SOL_ADDR if q.data=="dep_sol" else LTC_ADDR; bio=make_qr(addr)
        try: await q.message.delete()
        except: pass
        await context.bot.send_photo(chat_id=q.from_user.id, photo=bio, caption=f"Deposit to:\n`{addr}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Submit TXID", callback_data="sub_"+q.data.split("_")[1])]]))
    elif q.data.startswith("sub_"): context.user_data['w']='tx_'+q.data.split("_")[1]; await context.bot.send_message(chat_id=q.from_user.id, text="Send TXID:")
    elif q.data=="history":
        txt="📜 History:\n\n"
        for h in history.get(uid,[])[-20:][::-1]: txt+=f"{h['brand']} ${h['amount']} - ${h['price']} {h['date']}\nCode: {h['code']}\n\n"
        if not history.get(uid): txt+="No history"
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="profile")]]))
    elif q.data=="vendor":
        if not users[uid].get("is_seller"): await q.edit_message_text("Seller need $20", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Buy", callback_data="buy_seller")]])); return
        my={k:v for k,v in products.items() if v.get('seller_id')==uid}; t=f"🏪 Vendor {len(my)} items\n\n"; kb=[]
        for pid,p in my.items(): t+=f"{p['brand']} ${p['amount']} -> ${p['sell_price']}\n"; kb.append([InlineKeyboardButton(f"Remove {p['brand']}", callback_data=f"del_{pid}")])
        kb.append([InlineKeyboardButton("➕ Add Gift", callback_data="a_add")]); kb.append([InlineKeyboardButton("Back", callback_data="profile")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("del_"):
        pid=q.data.split("_",1)[1]
        if pid in products and (products[pid].get('seller_id')==uid or uid_int==ADMIN): del products[pid]; save("products.json",products)
        await q.edit_message_text("Deleted", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="vendor")]]))
    elif q.data.startswith("resell_"):
        if not users[uid].get("can_resell"): await q.edit_message_text("Need Re-sell $10", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Buy", callback_data="buy_resell")]])); return
        _, brand, code, amount = q.data.split("_",3); context.user_data['resell']=(brand,code,float(amount)); context.user_data['w']='resell_price'; await q.edit_message_text(f"Resell {brand} ${amount}\nEnter price:")
    elif q.data=="transfer": context.user_data['w']='transfer'; await q.edit_message_text("Format: @username amount\nEx: @toma 5")
    elif q.data=="redeem": context.user_data['w']='redeem'; await q.edit_message_text("Send redeem code:")
    elif q.data=="admin":
        if uid_int!=ADMIN: return
        await q.edit_message_text(f"👑 Admin\nUsers: {len(users)} Listings: {len(products)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add", callback_data="a_add")],[InlineKeyboardButton("📋 List/Del", callback_data="a_list")],[InlineKeyboardButton("👥 Users", callback_data="a_users")],[InlineKeyboardButton("💸 Add Bal", callback_data="a_bal")],[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="a_add": context.user_data['w']='add_gift'; await q.edit_message_text("Send: BRAND CODE $AMOUNT\nEx: STEAM XYZ123 $25", parse_mode="Markdown")
    elif q.data=="a_list":
        t=""; kb=[]
        for pid,p in products.items(): t+=f"{p['brand']} ${p['amount']} -> ${p['sell_price']} s:{p.get('seller_id')}\n"; kb.append([InlineKeyboardButton(f"Del {p['brand']}", callback_data=f"del_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="admin")]); await q.edit_message_text(t or "Empty", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="a_users":
        t="";
        for k,v in list(users.items())[:25]: t+=f"{k} @{v.get('username')} ${v.get('balance')} pur:{v.get('purchases',0)}\n"
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
    elif q.data=="a_bal": context.user_data['w']='bal'; await q.edit_message_text("UserID Amount\nEx: 12345 10")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    w=context.user_data.get('w'); txt=update.message.text.strip()
    users=load("users.json"); products=load("products.json")
    if w and w.startswith('tx_'):
        await context.bot.send_message(chat_id=ADMIN, text=f"💰 NEW DEPOSIT {w}\nFrom {update.effective_user.id} @{update.effective_user.username}\nTX: {txt}")
        await update.message.reply_text("✅ TX submitted"); context.user_data['w']=None; return
    if w=='transfer':
        try:
            a=txt.split(); uname=a[0].replace('@',''); amt=float(a[1]); target=None
            for k,v in users.items():
                if v.get('username','').lower()==uname.lower(): target=k; break
            if not target: await update.message.reply_text("User not found"); return
            uid=str(update.effective_user.id)
            if users[uid].get('balance',0)<amt: await update.message.reply_text("Low balance"); return
            users[uid]['balance']-=amt; users[target]['balance']=users[target].get('balance',0)+amt; save("users.json",users); await update.message.reply_text(f"✅ Sent ${amt} to @{uname}")
        except: await update.message.reply_text("Format: @username amount")
        context.user_data['w']=None; return
    if w=='add_gift':
        try:
            brand,code,amount,h=parse_gift(txt)
            if any(p.get('hash')==h for p in products.values()): await update.message.reply_text("❌ Same code already listed"); context.user_data['w']=None; return
            pid=f"{brand}_{h[:8]}_{random.randint(100,999)}"
            products[pid]={"brand":brand,"code":code,"amount":amount,"sell_price":round(amount*0.8,2),"hash":h,"seller_id":str(update.effective_user.id)}
            save("products.json",products); await send_stock(context, products[pid]); await update.message.reply_text(f"✅ Added {brand} ${amount} -> ${products[pid]['sell_price']}")
        except Exception as e: await update.message.reply_text(f"Error: {e}")
        context.user_data['w']=None; return
    if w=='resell_price':
        try:
            price=float(txt); brand,code,amount=context.user_data['resell']; h=hashlib.sha256(code.lower().strip().encode()).hexdigest()
            if any(p.get('hash')==h for p in products.values()): await update.message.reply_text("Already listed"); context.user_data['w']=None; return
            pid=f"R_{h[:8]}_{random.randint(100,999)}"
            products[pid]={"brand":brand,"code":code,"amount":amount,"sell_price":price,"hash":h,"seller_id":str(update.effective_user.id),"is_resale":True,"original_buyer":str(update.effective_user.id)}
            save("products.json",products); await update.message.reply_text(f"✅ Relisted for ${price}, you get 35% next sale")
        except: await update.message.reply_text("Enter valid number")
        context.user_data['w']=None; return
    if w=='bal':
        try:
            uid2,amt=txt.split(); amt=float(amt)
            if uid2 not in users: users[uid2]={"balance":0,"username":"","purchases":0,"spent":0,"is_seller":False,"can_resell":False}
            users[uid2]["balance"]=users[uid2].get("balance",0)+amt; save("users.json",users); await update.message.reply_text(f"Added ${amt} to {uid2}")
        except: await update.message.reply_text("Format: UserID Amount")
        context.user_data['w']=None; return
    # seller direct add without / command
    if users.get(str(update.effective_user.id),{}).get('is_seller') and '$' in txt:
        try:
            brand,code,amount,h=parse_gift(txt)
            if any(p.get('hash')==h for p in products.values()): await update.message.reply_text("❌ Already listed"); return
            pid=f"{brand}_{h[:8]}_{random.randint(100,999)}"
            products[pid]={"brand":brand,"code":code,"amount":amount,"sell_price":round(amount*0.8,2),"hash":h,"seller_id":str(update.effective_user.id)}
            save("products.json",products); await update.message.reply_text(f"✅ Listed {brand} ${amount}")
        except: pass

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mh))
    app.post_init=set_commands
    app.run_polling()

if __name__=="__main__": main()
