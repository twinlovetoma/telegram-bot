import os, json, threading, qrcode
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
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

def get_main_menu(uid_int):
    # FIX 1: Admin Panel sudhu admin dekhbe
    # FIX 2: Browse Gifts -> Latest Listing
    # FIX 3: Balance / Deposit alada
    kb = [
        [InlineKeyboardButton("🔥 Latest Listings", callback_data="browse")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("💵 Deposit", callback_data="deposit")]
    ]
    if uid_int == ADMIN:
        kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

async def send_to_stock_channel(context, product_id, product):
    if not STOCK_CHANNEL: return
    try:
        bal = product.get('card_balance',0)
        price = product.get('sell_price',0)
        status = product.get('status','')
        preview = product.get('details','')[:6] + "****"
        total = len(load("products.json"))
        text = f"🔥 NEW STOCK ADDED 🔥\n\nSerial: {product_id}\nBalance: ${bal}\nPrice: ${price}\nStatus: {status}\nPreview: {preview}\n\nTotal: {total}"
        await context.bot.send_message(chat_id=STOCK_CHANNEL, text=text)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json")
    uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0}
        save("users.json",users)

    # FIX 4: Welcome message with username
    user = update.effective_user
    username = f"@{user.username}" if user.username else ""
    first_name = user.first_name

    welcome_text = f"""
🎉 Welcome {first_name} {username}!

👋 Welcome to Prepaid Gift Store!

✨ Sell, Buy, and strike deals in seconds!!
🔒 All transactions are secure and transparent.

🎁 All types of cards are available here at best rates.

⭐ Earn $0.01 for each friend you refer!
Use /ref to get your referral link
"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(update.effective_user.id))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    try: await q.answer()
    except: pass
    users=load("users.json")
    products=load("products.json")
    uid=str(q.from_user.id)
    uid_int = q.from_user.id

    if q.data=="browse":
        if not products:
            await q.edit_message_text("No items - No latest listings available", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        t="🔥 Latest Listings:\n\n"; kb=[]
        for pid,p in products.items():
            bal=p.get('card_balance',0); price=p.get('sell_price',0); status=p.get('status','')
            preview=p.get('details','')[:6] + "****"
            t+=f"{pid} | Balance ${bal} | Price ${price} | Status {status} | {preview}\n"
            kb.append([InlineKeyboardButton(f"Buy {pid} - ${price}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("buy_"):
        pid=q.data.split("_")[1]; p=products.get(pid)
        if not p: return
        bal=p.get('card_balance',0); price=p.get('sell_price',0)
        preview=p.get('details','')[:6]
        txt=f"Serial: {pid}\nBalance: ${bal}\nPrice: ${price}\nStatus: {p.get('status')}\nPreview: {preview}****"
        kb=[[InlineKeyboardButton(f"Confirm Buy ${price}", callback_data=f"confirm_{pid}")],[InlineKeyboardButton("Back", callback_data="browse")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data.startswith("confirm_"):
        pid=q.data.split("_")[1]; p=products.get(pid)
        if not p: await q.edit_message_text("Sold out"); return
        price=float(p.get('sell_price',0)); bal=users.get(uid,{}).get("balance",0)
        if bal < price:
            await q.edit_message_text(f"Low balance. Need ${price} you have ${bal}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Deposit", callback_data="deposit")],[InlineKeyboardButton("Back", callback_data="back")]]))
            return
        users[uid]["balance"]=bal-price; save("users.json",users)
        del products[pid]; save("products.json",products)
        if STOCK_CHANNEL:
            try: await context.bot.send_message(chat_id=STOCK_CHANNEL, text=f"✅ SOLD: {pid} Remaining: {len(products)}")
            except: pass
        await q.edit_message_text(f"SUCCESS! Serial {pid}\nDetails:\n{p.get('details')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="back")]]))

    elif q.data=="back":
        await q.edit_message_text("Main Menu", reply_markup=get_main_menu(uid_int))

    elif q.data=="balance":
        b=users.get(uid,{}).get("balance",0)
        kb=[[InlineKeyboardButton("Deposit SOL / LTC", callback_data="deposit")],[InlineKeyboardButton("Back", callback_data="back")]]
        await q.edit_message_text(f"💰 Your Balance: ${b}", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="deposit":
        kb=[[InlineKeyboardButton("SOL Deposit", callback_data="dep_sol")],[InlineKeyboardButton("LTC Deposit", callback_data="dep_ltc")],[InlineKeyboardButton("Back", callback_data="balance")]]
        await q.edit_message_text("💵 Select Deposit Method:", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="dep_sol":
        bio = make_qr(SOL_ADDR)
        caption = f"⚡ X PREPAIDS STOCK — SOL DEPOSIT ⚡\n\nDeposit Address:\n`{SOL_ADDR}`\n\nMinimum Deposit: 0.05 SOL\n\nSend SOL to this address. Your balance will update automatically after confirmation.\n\n⚠️ WARNING:\n- Deposits below the minimum amount will not be processed.\n\n⚠️ Note: This deposit session is only active for 30 minutes."
        kb=[[InlineKeyboardButton("I Sent - Submit TXID", callback_data="sub_sol")],[InlineKeyboardButton("Back", callback_data="deposit")]]
        try: await q.message.delete()
        except: pass
        await context.bot.send_photo(chat_id=q.from_user.id, photo=bio, caption=caption, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="dep_ltc":
        bio = make_qr(LTC_ADDR)
        caption = f"⚡ X PREPAIDS STOCK — LTC DEPOSIT ⚡\n\nDeposit Address:\n`{LTC_ADDR}`\n\nMinimum: $5 LTC\n\nSend LTC to this address. Your balance will update automatically after confirmation."
        kb=[[InlineKeyboardButton("I Sent - Submit TXID", callback_data="sub_ltc")],[InlineKeyboardButton("Back", callback_data="deposit")]]
        try: await q.message.delete()
        except: pass
        await context.bot.send_photo(chat_id=q.from_user.id, photo=bio, caption=caption, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="sub_sol":
        context.user_data['w']='tx_sol'
        await context.bot.send_message(chat_id=q.from_user.id, text="Please send your SOL TXID / Hash:")
    elif q.data=="sub_ltc":
        context.user_data['w']='tx_ltc'
        await context.bot.send_message(chat_id=q.from_user.id, text="Please send your LTC TXID / Hash:")

    # ===== ADMIN ONLY =====
    elif q.data=="admin":
        if uid_int!= ADMIN:
            await q.edit_message_text("⛔ You are not admin!", reply_markup=get_main_menu(uid_int))
            return
        kb=[
            [InlineKeyboardButton("➕ Add Card", callback_data="a_add")],
            [InlineKeyboardButton("📋 List / Delete Cards", callback_data="a_list")],
            [InlineKeyboardButton("💸 Add Balance", callback_data="a_bal")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back")]
        ]
        await q.edit_message_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="a_add":
        if uid_int!= ADMIN: return
        context.user_data['w']='serial'
        await q.edit_message_text("1. Serial / ID? Ex: 435880")
    elif q.data=="a_list":
        if uid_int!= ADMIN: return
        if not products:
            await q.edit_message_text("No products", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]])); return
        t=""; kb=[]
        for pid,p in products.items():
            preview=p.get('details','')[:6]; t+=f"{pid} | ${p.get('card_balance')} | ${p.get('sell_price')} | {preview}****\n"
            kb.append([InlineKeyboardButton(f"Del {pid}", callback_data=f"dl_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="admin")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))
    elif q.data.startswith("dl_"):
        if uid_int!= ADMIN: return
        pid=q.data.split("_")[1]
        if pid in products: del products[pid]; save("products.json",products)
        await q.edit_message_text(f"Deleted {pid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))
    elif q.data=="a_bal":
        if uid_int!= ADMIN: return
        context.user_data['w']='bal'
        await q.edit_message_text("UserID Amount Ex: 123456 10")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    w=context.user_data.get('w')
    txt=update.message.text.strip()
    prods=load("products.json")
    if w=='tx_sol' or w=='tx_ltc':
        coin="SOL" if w=='tx_sol' else "LTC"
        try:
            await context.bot.send_message(chat_id=ADMIN, text=f"💰 NEW DEPOSIT {coin}\nFrom: {update.effective_user.id} @{update.effective_user.username}\nTX: {txt}")
            await update.message.reply_text(f"✅ {coin} TX submitted! Admin will confirm.")
        except: await update.message.reply_text("Submitted!")
        context.user_data['w']=None
        return
    if update.effective_user.id!=ADMIN: return
    if w=='serial':
        context.user_data['np']={"pid":txt}; context.user_data['w']='cb'
        await update.message.reply_text(f"Serial {txt} ok.\n2. Balance? Ex: 9.75")
    elif w=='cb':
        context.user_data['np']['card_balance']=float(txt); context.user_data['w']='sp'
        await update.message.reply_text("3. Price? Ex: 10")
    elif w=='sp':
        context.user_data['np']['sell_price']=float(txt); context.user_data['w']='st'
        await update.message.reply_text("4. Status? Ex: unregistered / registered")
    elif w=='st':
        context.user_data['np']['status']=txt; context.user_data['w']='wa'
        await update.message.reply_text("5. Warranty? Ex: 10 minutes")
    elif w=='wa':
        context.user_data['np']['warranty']=txt; context.user_data['w']='de'
        await update.message.reply_text("6. Full Details dao? (full mail)")
    elif w=='de':
        np=context.user_data['np']; pid=np['pid']
        prods[pid]={"name":pid,"card_balance":np['card_balance'],"sell_price":np['sell_price'],"status":np['status'],"warranty":np['warranty'],"details":txt}
        save("products.json",prods)
        await update.message.reply_text(f"Added {pid} Balance ${np['card_balance']} Price ${np['sell_price']}")
        await send_to_stock_channel(context, pid, prods[pid])
        context.user_data['w']=None
    elif w=='bal':
        try:
            uid2,amt=txt.split(); users=load("users.json")
            if uid2 not in users: users[uid2]={"balance":0}
            users[uid2]["balance"]+=float(amt); save("users.json",users)
            await update.message.reply_text(f"Added ${amt} to {uid2}")
            try: await context.bot.send_message(chat_id=int(uid2), text=f"✅ Deposit confirmed! ${amt} added. Balance: ${users[uid2]['balance']}")
            except: pass
            context.user_data['w']=None
        except: await update.message.reply_text("Format: UserID Amount")

# FIX 5: Side Menu like screenshot
async def set_commands(app):
    cmds = [
        BotCommand("start", "Launch the bot and view the main menu"),
        BotCommand("listings", "Browse all available cards"),
        BotCommand("unregistered_listing", "Show cards marked as UNREGISTERED"),
        BotCommand("cents_listing", "Show cards with balance less than $0.99"),
        BotCommand("listing_filter", "Filter cards by BIN"),
        BotCommand("listing_range", "Filter cards by Balance range"),
        BotCommand("check", "you can check cards here"),
        BotCommand("profile", "View your profile"),
        BotCommand("balance", "View your balances"),
        BotCommand("deposit", "Deposit SOL and LTC to your wallet"),
        BotCommand("withdraw", "Withdraw your balance"),
        BotCommand("ref", "Access your referral system and bonus"),
        BotCommand("redeem", "Redeem a balance top-up code"),
    ]
    await app.bot.set_my_commands(cmds)

def main():
    application=Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(cb))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mh))
    application.post_init = set_commands
    application.run_polling()

if __name__=="__main__":
    main()
