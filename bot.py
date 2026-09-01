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
    qr=qrcode.QRCode(box_size=10, border=2); qr.add_data(text); qr.make(fit=True)
    img=qr.make_image(fill_color="black", back_color="white"); bio=BytesIO(); img.save(bio,'PNG'); bio.seek(0); return bio

def parse_card(text):
    m = re.search(r'\$\s*(\d+(?:\.\d+)?)', text)
    balance = float(m.group(1)) if m else float(re.findall(r'(\d+(?:\.\d+)?)', text)[-1])
    bin_code = re.search(r'(\d{6})', text).group(1) if re.search(r'(\d{6})', text) else "000000"
    serial = f"{bin_code}{random.randint(1000,9999)}"
    return serial, bin_code, balance

def get_main_menu(uid_int):
    kb=[
        [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")]
    ]
    if uid_int==ADMIN: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

async def send_to_stock_channel(context, pid, p):
    if not STOCK_CHANNEL: return
    try:
        text=f"""🔥 NEW STOCK ADDED 🔥

💳 BIN: {p.get('bin')}
💰 Balance: ${p.get('card_balance')}
💵 Price: ${p.get('sell_price')}
📌 Status: {p.get('status')}
🔍 G used: {'✅' if p.get('g_used') else '❌'}
📱 P used: {'✅' if p.get('p_used') else '❌'}

📦 Total Stock: {len(load('products.json'))}"""
        await context.bot.send_message(chat_id=STOCK_CHANNEL, text=text)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json"); uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0,"username":update.effective_user.username,"first_name":update.effective_user.first_name,"joined":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        save("users.json",users)
    u=update.effective_user
    await update.message.reply_text(f"🎉 Welcome {u.first_name} @{u.username if u.username else ''}!\n\n👋 Welcome to Prepaid Gift Store!", reply_markup=get_main_menu(u.id))

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json"); history=load("history.json"); uid=str(update.effective_user.id)
    u=users.get(uid,{}); bal=u.get("balance",0)
    txt=f"👤 YOUR PROFILE\n\n🆔 User ID: `{uid}`\n👤 Name: {update.effective_user.first_name}\n🔗 Username: @{update.effective_user.username}\n💰 Balance: ${bal}\n📅 Joined: {u.get('joined','N/A')}\n\n📦 BUYING HISTORY:\n"
    for h in history.get(uid,[])[-10:][::-1]: txt+=f"• {h.get('pid')} - ${h.get('price')} on {h.get('date')}\n"
    if not history.get(uid): txt+="No purchases yet."
    await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    users=load("users.json"); products=load("products.json"); history=load("history.json")
    uid=str(q.from_user.id); uid_int=q.from_user.id
    np=context.user_data.get('np',{})

    if q.data=="browse":
        if not products: await q.edit_message_text("No latest listings", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]])); return
        t="🔥 Latest Listings:\n\n"
        kb=[]
        for pid,p in products.items():
            t+=f"{p.get('bin')} | ${p.get('card_balance')} | ${p.get('sell_price')} | {p.get('status')} G:{'✅' if p.get('g_used') else '❌'} P:{'✅' if p.get('p_used') else '❌'}\n"
            kb.append([InlineKeyboardButton(f"Buy {p.get('bin')} - ${p.get('sell_price')}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("buy_"):
        pid=q.data.split("_")[1]; p=products[pid]
        await q.edit_message_text(f"BIN: {p.get('bin')}\nBalance: ${p.get('card_balance')}\nPrice: ${p.get('sell_price')}\nStatus: {p.get('status')}\nG used: {'✅' if p.get('g_used') else '❌'}\nP used: {'✅' if p.get('p_used') else '❌'}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Confirm Buy ${p.get('sell_price')}", callback_data=f"confirm_{pid}")],[InlineKeyboardButton("Back", callback_data="browse")]]))

    elif q.data.startswith("confirm_"):
        pid=q.data.split("_")[1]; p=products[pid]; price=float(p['sell_price']); bal=users.get(uid,{}).get("balance",0)
        if bal<price: await q.edit_message_text(f"Low balance Need ${price} have ${bal}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")]])); return
        users[uid]["balance"]=bal-price; save("users.json",users)
        if uid not in history: history[uid]=[]
        history[uid].append({"pid":p.get('bin'),"price":price,"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}); save("history.json",history)
        del products[pid]; save("products.json",products)
        await q.edit_message_text(f"✅ SUCCESS!\n{p.get('details')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif q.data=="back": await q.edit_message_text("Main Menu", reply_markup=get_main_menu(uid_int))
    elif q.data=="profile":
        bal=users.get(uid,{}).get("balance",0); joined=users.get(uid,{}).get("joined","N/A")
        txt=f"👤 PROFILE\n\n🆔 ID: `{uid}`\n👤 Name: {q.from_user.first_name}\n🔗 Username: @{q.from_user.username}\n💰 Balance: ${bal}\n📅 Joined: {joined}\n\n📦 BUYING HISTORY:\n"
        for h in history.get(uid,[])[-10:][::-1]: txt+=f"• {h.get('pid')} - ${h.get('price')} on {h.get('date')}\n"
        if not history.get(uid): txt+="No purchases yet."
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif q.data=="balance": await q.edit_message_text(f"💰 Balance: ${users.get(uid,{}).get('balance',0)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")],[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data=="deposit": await q.edit_message_text("💵 Select:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SOL", callback_data="dep_sol")],[InlineKeyboardButton("LTC", callback_data="dep_ltc")],[InlineKeyboardButton("Back", callback_data="back")]]))
    elif q.data in ["dep_sol","dep_ltc"]:
        addr=SOL_ADDR if q.data=="dep_sol" else LTC_ADDR; bio=make_qr(addr)
        try: await q.message.delete()
        except: pass
        await context.bot.send_photo(chat_id=q.from_user.id, photo=bio, caption=f"Deposit to:\n`{addr}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Submit TXID", callback_data="sub_"+q.data.split("_")[1])],[InlineKeyboardButton("Back", callback_data="deposit")]]))
    elif q.data.startswith("sub_"): context.user_data['w']='tx_'+q.data.split("_")[1]; await context.bot.send_message(chat_id=q.from_user.id, text="Send TXID:")

    elif q.data=="admin":
        if uid_int!=ADMIN: return
        await q.edit_message_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Card", callback_data="a_add")],[InlineKeyboardButton("📋 List / Delete", callback_data="a_list")],[InlineKeyboardButton("💸 Add Balance", callback_data="a_bal")],[InlineKeyboardButton("⬅️ Back", callback_data="back")]]))

    elif q.data=="a_add":
        context.user_data['w']='full_details'
        await q.edit_message_text("📩 Send Full Details with Balance\nExample:\n`435880518684xxxx:08:28:085 $25`\n\nBot auto detect BIN & Balance + Price 39% auto", parse_mode="Markdown")

    elif q.data.startswith("toggle_"):
        key=q.data.split("_")[1]
        if key=="status": np['status']="Unregistered" if np.get('status')=="Registered" else "Registered"
        elif key=="g": np['g_used']=not np.get('g_used',False)
        elif key=="p": np['p_used']=not np.get('p_used',False)
        context.user_data['np']=np
        kb=[
            [InlineKeyboardButton(f"📌 Status: {np.get('status')}", callback_data="toggle_status")],
            [InlineKeyboardButton(f"🔍 G used: {'✅' if np.get('g_used') else '❌'}", callback_data="toggle_g")],
            [InlineKeyboardButton(f"📱 P used: {'✅' if np.get('p_used') else '❌'}", callback_data="toggle_p")],
            [InlineKeyboardButton(f"💵 Price: ${np.get('sell_price')} (39%)", callback_data="change_price")],
            [InlineKeyboardButton("✅ Confirm Add", callback_data="final_add")]
        ]
        await q.edit_message_text(f"BIN: {np.get('bin')} Bal: ${np.get('card_balance')} Price: ${np.get('sell_price')}\nDetails: `{np.get('details')}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="change_price": context.user_data['w']='set_price'; await q.edit_message_text("Enter Price Ex: 10")
    elif q.data=="final_add":
        prods=load("products.json"); pid=np['pid']
        prods[pid]={"bin":np['bin'],"card_balance":np['card_balance'],"sell_price":np['sell_price'],"status":np['status'],"g_used":np['g_used'],"p_used":np['p_used'],"details":np['details']}
        save("products.json",prods); await q.edit_message_text(f"✅ Added BIN {np['bin']} Bal ${np['card_balance']} Price ${np['sell_price']}"); await send_to_stock_channel(context, pid, prods[pid]); context.user_data['np']={}

    elif q.data=="a_list":
        if not products: await q.edit_message_text("No products", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]])); return
        t=""; kb=[]
        for pid,p in products.items(): t+=f"{p.get('bin')} | ${p.get('card_balance')} | ${p.get('sell_price')}\n"; kb.append([InlineKeyboardButton(f"Del {p.get('bin')}", callback_data=f"dl_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="admin")]); await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("dl_"):
        pid=q.data.split("_")[1];
        if pid in products: del products[pid]; save("products.json",products)
        await q.edit_message_text(f"Deleted {pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
    elif q.data=="a_bal": context.user_data['w']='bal'; await q.edit_message_text("UserID Amount Ex: 123456 10")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    w=context.user_data.get('w'); txt=update.message.text.strip()
    if w and w.startswith('tx_'):
        await context.bot.send_message(chat_id=ADMIN, text=f"💰 NEW DEPOSIT {w}\nFrom: {update.effective_user.id} @{update.effective_user.username}\nTX: {txt}")
        await update.message.reply_text("✅ TX submitted!"); context.user_data['w']=None; return
    if update.effective_user.id!=ADMIN: return
    if w=='full_details':
        serial, bin_code, balance = parse_card(txt)
        auto_price = round(balance * 0.39, 2)
        context.user_data['np']={"pid":serial,"bin":bin_code,"card_balance":balance,"details":txt,"status":"Registered","g_used":False,"p_used":False,"sell_price":auto_price}
        kb=[
            [InlineKeyboardButton(f"📌 Status: Registered", callback_data="toggle_status")],
            [InlineKeyboardButton(f"🔍 G used: ❌", callback_data="toggle_g")],
            [InlineKeyboardButton(f"📱 P used: ❌", callback_data="toggle_p")],
            [InlineKeyboardButton(f"💵 Price: ${auto_price} (39% auto)", callback_data="change_price")],
            [InlineKeyboardButton("✅ Confirm Add to Stock", callback_data="final_add")]
        ]
        await update.message.reply_text(f"✅ Parsed!\nBIN: {bin_code}\nBalance: ${balance}\nPrice Auto 39%: ${auto_price}\n\nSet G/P/Status:", reply_markup=InlineKeyboardMarkup(kb))
        context.user_data['w']=None
    elif w=='set_price':
        try:
            context.user_data['np']['sell_price']=float(txt)
            np=context.user_data['np']
            kb=[[InlineKeyboardButton(f"📌 Status: {np.get('status')}", callback_data="toggle_status")],[InlineKeyboardButton(f"🔍 G used: {'✅' if np.get('g_used') else '❌'}", callback_data="toggle_g")],[InlineKeyboardButton(f"📱 P used: {'✅' if np.get('p_used') else '❌'}", callback_data="toggle_p")],[InlineKeyboardButton(f"💵 Price: ${np.get('sell_price')}", callback_data="change_price")],[InlineKeyboardButton("✅ Confirm Add", callback_data="final_add")]]
            await update.message.reply_text(f"Price updated to ${txt}", reply_markup=InlineKeyboardMarkup(kb)); context.user_data['w']=None
        except: await update.message.reply_text("Number dao Ex: 9.75")
    elif w=='bal':
        try:
            uid2,amt=txt.split(); users=load("users.json")
            if uid2 not in users: users[uid2]={"balance":0}
            users[uid2]["balance"]+=float(amt); save("users.json",users); await update.message.reply_text(f"Added ${amt} to {uid2}"); context.user_data['w']=None
        except: await update.message.reply_text("Format: UserID Amount")

async def set_commands(app):
    cmds=[BotCommand("start","Launch bot"),BotCommand("profile","View profile"),BotCommand("balance","View balance"),BotCommand("deposit","Deposit"),BotCommand("listings","Browse cards")]
    await app.bot.set_my_commands(cmds)

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mh))
    app.post_init=set_commands
    app.run_polling()

if __name__=="__main__": main()
