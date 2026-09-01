import os, json, hashlib, re, time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "0"))
CHANNEL = os.getenv("STOCK_CHANNEL")

def load(f):
    try:
        with open(f,"r") as fp: return json.load(fp)
    except: return {}
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
    await update.message.reply_text(f"🎉 Welcome {update.effective_user.first_name}!\n👋 Gift Code Store", reply_markup=InlineKeyboardMarkup(kb))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    d=q.data
    uid=str(q.from_user.id)
    users=load("users.json")
    products=load("products.json")
    settings=load("settings.json")
    if not settings: settings={"perc":65}

    if d=="browse":
        if not products:
            await q.edit_message_text("No stock", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
            return
        txt="🔥 Stock:\n\n"
        kb=[]
        for pid,p in list(products.items())[:15]:
            txt+=f"{p['brand']} -> ${p['sell_price']}\n"
            kb.append([InlineKeyboardButton(f"Buy {p['brand'][:15]} ${p['sell_price']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif d=="back":
        kb=[
            [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
            [InlineKeyboardButton("💰 My Balance", callback_data="bal")],
            [InlineKeyboardButton("💵 Deposit", callback_data="dep")],
            [InlineKeyboardButton("👤 My Profile", callback_data="prof")]
        ]
        await q.edit_message_text("Main Menu", reply_markup=InlineKeyboardMarkup(kb))

    elif d=="bal":
        b=users.get(uid,{}).get("balance",0)
        await q.edit_message_text(f"Balance: ${b}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif d=="dep":
        await q.edit_message_text(f"Deposit ID: {uid}\nContact Admin", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif d=="prof":
        b=users.get(uid,{}).get("balance",0)
        kb=[[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        if q.from_user.id==ADMIN:
            kb.append([InlineKeyboardButton("👑 Admin", callback_data="admin")])
        await q.edit_message_text(f"ID: {uid}\nBal: ${b}", reply_markup=InlineKeyboardMarkup(kb))

    elif d=="admin" and q.from_user.id==ADMIN:
        kb=[
            [InlineKeyboardButton("➕ Add Stock", callback_data="add")],
            [InlineKeyboardButton("💲 Set % Price", callback_data="setp")],
            [InlineKeyboardButton("💵 Add Balance", callback_data="ab")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await q.edit_message_text(f"Admin Panel\nPerc: {settings.get('perc',65)}% Items: {len(products)}", reply_markup=InlineKeyboardMarkup(kb))

    elif d=="add" and q.from_user.id==ADMIN:
        context.user_data['w']='add'
        await q.edit_message_text("Send list:\nEx: CODM 420 CP $5\nOne per line")

    elif d=="setp" and q.from_user.id==ADMIN:
        context.user_data['w']='perc'
        await q.edit_message_text("Send % number\nEx: 50")

    elif d=="ab" and q.from_user.id==ADMIN:
        context.user_data['w']='ab'
        await q.edit_message_text("Send: USERID AMOUNT\nEx: 123456 10")

    elif d.startswith("buy_"):
        pid=d.split("buy_")[1]
        p=products.get(pid)
        if not p:
            await q.edit_message_text("Sold out", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="browse")]]))
            return
        if users[uid]["balance"] < float(p["sell_price"]):
            await q.edit_message_text("Low Balance", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💵 Deposit", callback_data="dep")],[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))
            return
        users[uid]["balance"]-=float(p["sell_price"])
        save("users.json",users)
        code=p["code"]
        del products[pid]
        save("products.json",products)
        await q.edit_message_text(f"✅ Delivered:\n{code}")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    w=context.user_data.get('w')
    if w=='add':
        products=load("products.json")
        settings=load("settings.json")
        if not settings: settings={"perc":65}
        perc=settings.get("perc",65)
        cnt=0
        for line in txt.split('\n'):
            if '$' not in line: continue
            try:
                m=re.search(r'\$\s*(\d+(?:\.\d+)?)', line)
                if not m: continue
                amt=float(m.group(1))
                brand=line.split('$')[0].strip()[:30]
                if len(brand)<2: continue
                pid=hashlib.md5(f"{brand}{time.time()}{cnt}".encode()).hexdigest()[:8]
                sell=round(amt*perc/100,2)
                products[pid]={"brand":brand,"code":brand,"amount":amt,"sell_price":sell}
                cnt+=1
                if CHANNEL:
                    try:
                        await context.bot.send_message(chat_id=CHANNEL, text=f"🆕 NEW STOCK\n{brand}\n💲 ${sell} (MRP ${amt})")
                    except: pass
            except: pass
        save("products.json",products)
        await update.message.reply_text(f"✅ {cnt} items added & posted to channel")
        context.user_data['w']=None

    elif w=='perc':
        try:
            p=float(txt.replace('%','').strip())
            settings=load("settings.json")
            if not settings: settings={}
            settings["perc"]=p
            save("settings.json",settings)
            products=load("products.json")
            for k in products:
                products[k]["sell_price"]=round(float(products[k]["amount"])*p/100,2)
            save("products.json",products)
            await update.message.reply_text(f"✅ All set to {p}%")
            if CHANNEL:
                try:
                    await context.bot.send_message(chat_id=CHANNEL, text=f"💲 PRICE UPDATE\nAll items now {p}%\n$10 -> ${round(10*p/100,2)}")
                except: pass
        except:
            await update.message.reply_text("Invalid %")
        context.user_data['w']=None

    elif w=='ab':
        try:
            uid2,amt=txt.split()
            amt=float(amt)
            users=load("users.json")
            if uid2 not in users: users[uid2]={"balance":0,"is_seller":False}
            users[uid2]["balance"]=users[uid2].get("balance",0)+amt
            save("users.json",users)
            await update.message.reply_text(f"Added ${amt} to {uid2}")
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
