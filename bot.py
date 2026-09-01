import os, json, threading, qrcode, re, random
from datetime import datetime
from io import BytesIO
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL = os.getenv("STOCK_CHANNEL_ID", "")
SOL_ADDR = os.getenv("SOL_ADDRESS", "Not set")
LTC_ADDR = os.getenv("LTC_ADDRESS", "Not set")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "OK"
threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000))), daemon=True).start()

def load(f):
    if not os.path.exists(f): return {}
    try:
        with open(f,'r', encoding='utf-8') as x: return json.load(x)
    except: return {}
def save(f,d):
    with open(f,'w', encoding='utf-8') as x: json.dump(d,x,indent=2)

def make_qr(text):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(text); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO(); img.save(bio, 'PNG'); bio.seek(0); return bio

def parse_card_details(text):
    # Example: 435880518684xxxx:08:28:085 $25
    bal_match = re.findall(r'\$?\s*(\d+(?:\.\d+)?)', text)
    balance = 0.0
    if bal_match:
        # last number is usually balance if $ present, otherwise try to find $xx
        m = re.search(r'\$\s*(\d+(?:\.\d+)?)', text)
        if m: balance = float(m.group(1))
        else: balance = float(bal_match[-1])
    bin_match = re.search(r'(\d{6})', text)
    bin_code = bin_match.group(1) if bin_match else "000000"
    serial = f"{bin_code}{random.randint(1000,9999)}"
    return serial, bin_code, balance

def get_main_menu(uid_int):
    kb = [
        [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")]
    ]
    if uid_int == ADMIN:
        kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

async def send_to_stock_channel(context, product_id, product):
    if not STOCK_CHANNEL: return
    try:
        bal = product.get('card_balance',0)
        price = product.get('sell_price',0)
        status = product.get('status','Registered')
        bin_code = product.get('bin', product_id)
        g_used = "✅" if product.get('g_used') else "❌"
        p_used = "✅" if product.get('p_used') else "❌"
        total = len(load("products.json"))
        text = f"""🔥 NEW STOCK ADDED 🔥

💳 BIN: {bin_code}
💰 Balance: ${bal}
💵 Price: ${price}
📌 Status: {status}
🔍 G used: {g_used}
📱 P used: {p_used}

📦 Total Stock: {total}"""
        await context.bot.send_message(chat_id=STOCK_CHANNEL, text=text)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json")
    uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0,"username":update.effective_user.username,"first_name":update.effective_user.first_name,"joined":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        save("users.json",users)
    user = update.effective_user
    username = f"@{user.username}" if user.username else ""
    welcome_text = f"""🎉 Welcome {user.first_name} {username}!

👋 Welcome to Prepaid Gift Store!

✨ Sell, Buy, and strike deals in seconds!!
🔒 All transactions are secure and transparent.

🎁 All types of cards are available here at best rates.

⭐ Earn $0.01 for each friend you refer!
Use /ref to get your referral link"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(update.effective_user.id))

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json"); history=load("history.json")
    uid=str(update.effective_user.id)
    u=users.get(uid,{})
    bal=u.get("balance",0); joined=u.get("joined","N/A")
    text = f"""👤 YOUR PROFILE

🆔 User ID: `{uid}`
👤 Name: {update.effective_user.first_name}
🔗 Username: @{update.effective_user.username if update.effective_user.username else 'No username'}
💰 Balance: ${bal}
📅 Joined: {joined}

📦 BUYING HISTORY:
"""
    h_list = history.get(uid, [])
    if not h_list:
        text += "\nNo purchases yet."
    else:
        for h in h_list[-10:][::-1]:
            text += f"\n• BIN {h.get('pid')} - ${h.get('price')} on {h.get('date')}"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

async def profile_callback(q):
    users=load("users.json"); history=load("history.json")
    uid=str(q.from_user.id)
    u=users.get(uid,{})
    bal=u.get("balance",0); joined=u.get("joined","N/A")
    text = f"""👤 YOUR PROFILE

🆔 User ID: `{uid}`
👤 Name: {q.from_user.first_name}
🔗 Username: @{q.from_user.username if q.from_user.username else 'No username'}
💰 Balance: ${bal}
📅 Joined: {joined}

📦 BUYING HISTORY:
"""
    h_list = history.get(uid, [])
    if not h_list:
        text += "\nNo purchases yet."
    else:
        for h in h_list[-10:][::-1]:
            text += f"\n• BIN {h.get('pid')} - ${h.get('price')} on {h.get('date')}"
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    users=load("users.json"); products=load("products.json"); history=load("history.json")
    uid=str(q.from_user.id); uid_int=q.from_user.id
    np = context.user_data.get('np', {})

    if q.data=="browse":
        if not products:
            await q.edit_message_text("No items - No latest listings available", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])); return
        t="🔥 Latest Listings:\n\n"; kb=[]
        for pid,p in products.items():
            t+=f"{p.get('bin',pid)} | ${p.get('card_balance')} | ${p.get('sell_price')} | {p.get('status')} | G:{'✅' if p.get('g_used') else '❌'} P:{'✅' if p.get('p_used') else '❌'}\n"
            kb.append([InlineKeyboardButton(f"Buy {p.get('bin',pid)} - ${p.get('sell_price')}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("buy_"):
        pid=q.data.split("_")[1]; p=products.get(pid)
        if not p: return
        txt=f"💳 BIN: {p.get('bin')}\n💰 Balance: ${p.get('card_balance')}\n💵 Price: ${p.get('sell_price')}\n📌 Status: {p.get('status')}\n🔍 G used: {'✅' if p.get('g_used') else '❌'}\n📱 P used: {'✅' if p.get('p_used') else '❌'}"
        kb=[[InlineKeyboardButton(f"Confirm Buy ${p.get('sell_price')}", callback_data=f"confirm_{pid}")],[InlineKeyboardButton("Back", callback_data="browse")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("confirm_"):
        pid=q.data.split("_")[1]; p=products.get(pid)
        if not p: await q.edit_message_text("Sold out"); return
        price=float(p.get('sell_price',0)); bal=users.get(uid,{}).get("balance",0)
        if bal < price:
            await q.edit_message_text(f"Low balance. Need ${price} you have ${bal}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")],[InlineKeyboardButton("Back", callback_data="back")]])); return
        users[uid]["balance"]=bal-price; save("users.json",users)
        if uid not in history: history[uid]=[]
        history[uid].append({"pid":p.get('bin',pid),"price":price,"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"details":p.get('details')})
        save("history.json",history)
        del products[pid]; save("products.json",products)
        await q.edit_message_text(f"✅ SUCCESS! Serial {p.get('bin')}\nDetails:\n{p.get('details')}\n\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif q.data=="back":
        await q.edit_message_text("Main Menu", reply_markup=get_main_menu(uid_int))
    elif q.data=="profile":
        await profile_callback(q)
    elif q.data=="balance":
        b=users.get(uid,{}).get("balance",0)
        await q.edit_message_text(f"💰 Your Balance: ${b}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")],[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="deposit":
        kb=[[InlineKeyboardButton("SOL Deposit", callback_data="dep_sol")],[InlineKeyboardButton("LTC Deposit", callback_data="dep_ltc")],[InlineKeyboardButton("Back", callback_data="balance")]]
        await q.edit_message_text("💵 Select Deposit Method:", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="dep_sol":
        bio=make_qr(SOL_ADDR); cap=f"⚡ SOL DEPOSIT ⚡\n\n`{SOL_ADDR}`\nMin 0.05 SOL"
        kb=[[InlineKeyboardButton("I Sent - Submit TXID", callback_data="sub_sol")],[InlineKeyboardButton("Back", callback_data="deposit")]]
        try: await q.message.delete()
        except: pass
        await context.bot.send_photo(chat_id=q.from_user.id, photo=bio, caption=cap, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="dep_ltc":
        bio=make_qr(LTC_ADDR); cap=f"⚡ LTC DEPOSIT ⚡\n\n`{LTC_ADDR}`"
        kb=[[InlineKeyboardButton("I Sent - Submit TXID", callback_data="sub_ltc")],[InlineKeyboardButton("Back", callback_data="deposit")]]
        try: await q.message.delete()
        except: pass
        await context.bot.send_photo(chat_id=q.from_user.id, photo=bio, caption=cap, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("sub_"):
        context.user_data['w']='tx_'+q.data.split("_")[1]
        await context.bot.send_message(chat_id=q.from_user.id, text="Please send your TXID / Hash:")

    elif q.data=="admin":
        if uid_int!=ADMIN: await q.edit_message_text("⛔ Not admin!", reply_markup=get_main_menu(uid_int)); return
        kb=[[InlineKeyboardButton("➕ Add Card", callback_data="a_add")],[InlineKeyboardButton("📋 List / Delete Cards", callback_data="a_list")],[InlineKeyboardButton("💸 Add Balance", callback_data="a_bal")],[InlineKeyboardButton("⬅️ Back", callback_data="back")]]
        await q.edit_message_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="a_add":
        if uid_int!=ADMIN: return
        context.user_data['w']='full_details'
        await q.edit_message_text("📩 Send Full Details with Balance\n\nExample:\n`435880518684xxxx:08:28:085 $25`\n\nBot will auto detect BIN & Balance and set price 39%", parse_mode="Markdown")

    elif q.data.startswith("toggle_"):
        if uid_int!=ADMIN: return
        key=q.data.split("_")[1]
        if key=="status": np['status']="Unregistered" if np.get('status')=="Registered" else "Registered"
        elif key=="g": np['g_used']=not np.get('g_used',False)
        elif key=="p": np['p_used']=not np.get('p_used',False)
        context.user_data['np']=np
        kb=[
            [InlineKeyboardButton(f"📌 Status: {np.get('status')}", callback_data="toggle_status")],
            [InlineKeyboardButton(f"🔍 G used: {'✅' if np.get('g_used') else '❌'}", callback_data="toggle_g")],
            [InlineKeyboardButton(f"📱 P used: {'✅' if np.get('p_used') else '❌'}", callback_data="toggle_p")],
            [InlineKeyboardButton(f"💵 Price: ${np.get('sell_price')} (39% auto)", callback_data="change_price")],
            [InlineKeyboardButton("✅ Confirm Add to Stock", callback_data="final_add")],
            [InlineKeyboardButton("❌ Cancel", callback_data="admin")]
        ]
        await q.edit_message_text(f"Card Parsed:\nBIN: {np.get('bin')}\nBalance: ${np.get('card_balance')}\nPrice Auto 39%: ${np.get('sell_price')}\nDetails: `{np.get('details')}`\n\nSet options with buttons:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="change_price":
        if uid_int!=ADMIN: return
        context.user_data['w']='set_price'
        await q.edit_message_text("Enter New Price? Ex: 10\nCurrent 39% auto price will be overwritten")

    elif q.data=="final_add":
        if uid_int!=ADMIN: return
        prods=load("products.json")
        pid=np.get('pid')
        prods[pid]={"name":pid,"bin":np.get('bin'),"card_balance":np.get('card_balance'),"sell_price":np.get('sell_price'),"status":np.get('status','Registered'),"g_used":np.get('g_used',False),"p_used":np.get('p_used',False),"warranty":"10 minutes","details":np.get('details')}
        save("products.json",prods)
        await q.edit_message_text(f"✅ Added BIN {np.get('bin')} Balance ${np.get('card_balance')} Price ${np.get('sell_price')}")
        await send_to_stock_channel(context, pid, prods[pid])
        context.user_data['np']={}

    elif q.data=="a_list":
        if uid_int!=ADMIN: return
        if not products: await q.edit_message_text("No products", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]])); return
        t=""; kb=[]
        for pid,p in products.items():
            t+=f"{p.get('bin',pid)} | ${p.get('card_balance')} | ${p.get('sell_price')} | {p.get('status')}\n"
            kb.append([InlineKeyboardButton(f"Del {p.get('bin',pid)}", callback_data=f"dl_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="admin")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("dl_"):
        if uid_int!=ADMIN: return
        pid=q.data.split("_")[1]
        if pid in products: del products[pid]; save("products.json",products)
        await q.edit_message_text(f"Deleted {pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))

    elif q.data=="a_bal":
        if uid_int!=ADMIN: return
        context.user_data['w']='bal'
        await q.edit_message_text("UserID Amount Ex: 123456 10")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    w=context.user_data.get('w')
    txt=update.message.text.strip()
    if w and w.startswith('tx_'):
        coin="SOL" if w=='tx_sol' else "LTC"
        try: await context.bot.send_message(chat_id=ADMIN, text=f"💰 NEW DEPOSIT {coin}\nFrom: {update.effective_user.id} @{update.effective_user.username}\nTX: {txt}")
        except: pass
        await update.message.reply_text(f"✅ {coin} TX submitted! Admin will confirm.")
        context.user_data['w']=None
        return

    if update.effective_user.id!=ADMIN: return

    if w=='full_details':
        serial, bin_code, balance = parse_card_details(txt)
        auto_price = round(balance * 0.39, 2)
        context.user_data['np']={"pid":serial,"bin":bin_code,"card_balance":balance,"details":txt,"
