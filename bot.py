import os, json, uuid, threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7634497248"))
STOCK_CHANNEL = int(os.getenv("STOCK_CHANNEL", "-1001234567890"))

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot Live ✅"
@flask_app.route('/health')
def health(): return "OK"
threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT",10000))), daemon=True).start()

def load(f, default=None):
    if default is None: default={}
    if not os.path.exists(f): return default
    try:
        with open(f,'r') as j: return json.load(j)
    except: return default

def save(f,d):
    with open(f,'w') as j: json.dump(j, j, indent=2)

def get_config():
    return load("config.json", {"perc":65, "comm":5})

def admin_panel_text():
    cfg=get_config()
    products=load("products.json")
    stock_count = len([p for p in products.values() if not p.get('sold')])
    return f"👑 Admin Panel\nPerc: {cfg.get('perc',65)}%\nComm: {cfg.get('comm',5)}%\nStock: {stock_count}"

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Stock", callback_data="add_stock"), InlineKeyboardButton("💲 Set %", callback_data="set_perc")],
        [InlineKeyboardButton("💵 Add Balance", callback_data="add_balance"), InlineKeyboardButton("🔄 Relist", callback_data="relist")],
        [InlineKeyboardButton("🧑‍💼 Vendor Req", callback_data="vendor_req"), InlineKeyboardButton("👥 All Sellers", callback_data="all_sellers")],
        [InlineKeyboardButton("⏳ Pending Orders", callback_data="pending_orders"), InlineKeyboardButton("📊 Sales History", callback_data="sales_history")],
        [InlineKeyboardButton("📜 Buyer History", callback_data="buyer_history")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    if uid==ADMIN_ID:
        await update.message.reply_text(admin_panel_text(), reply_markup=admin_keyboard())
    else:
        await update.message.reply_text(f"🎉 Welcome {update.effective_user.first_name}!\n\n🎁 Best Gift Store!")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip()
    uid=update.effective_user.id
    if uid!=ADMIN_ID: return
    wait=context.user_data.get('wait')

    if wait=='add_balance':
        try:
            parts=txt.split()
            user_id=parts[0]
            amount=float(parts[1])
            users=load("users.json")
            if user_id not in users: users[user_id]={"balance":0}
            users[user_id]['balance']+=amount
            save("users.json", users)
            await update.message.reply_text(f"✅ ${amount} to {user_id}", reply_markup=admin_keyboard())
            try: await context.bot.send_message(chat_id=int(user_id), text=f"✅ ${amount} added to your balance!")
            except: pass
            context.user_data['wait']=None
        except:
            await update.message.reply_text("❌ Format: USERID AMOUNT\nEx: 6699688350 10")

    elif wait=='set_perc':
        try:
            perc=float(txt.replace("%",""))
            cfg=get_config()
            cfg['perc']=perc
            save("config.json", cfg)
            await update.message.reply_text(f"✅ {perc}% set", reply_markup=admin_keyboard())
            context.user_data['wait']=None
        except:
            await update.message.reply_text("❌ Send % ex: 65")

    elif wait=='add_stock':
        try:
            parts=txt.split()
            if len(parts)>=3:
                brand=parts[0]
                amount=parts[1]
                code=" ".join(parts[2:])
            else:
                await update.message.reply_text("❌ Format: BRAND AMOUNT CODE\nEx: Amazon 10 XYZ123")
                return

            products=load("products.json")
            # BUG FIX: Duplicate check
            for p in products.values():
                if p['code'].strip().lower()==code.strip().lower() and not p.get('sold'):
                    await update.message.reply_text(f"❌ Duplicate! Ei code already stock e ache:\n{p['brand']} ${p['amount']}", reply_markup=admin_keyboard())
                    return

            pid=str(uuid.uuid4())
            cfg=get_config()
            try: sell_price = float(amount)*cfg.get('perc',65)/100
            except: sell_price = 0

            products[pid]={"brand":brand, "amount":amount, "code":code, "sell_price":round(sell_price,2), "sold":False, "date": str(datetime.now())}
            save("products.json", products)

            # PREMIUM NEW STOCK NOTIFY TO CHANNEL
            try:
                new_stock_msg = f"""
╔═══════════════════╗
   🎁 NEW STOCK 🎁
╚═══════════════════╝

🔥 Brand: {brand}
💵 Amount: ${amount}
💲 Price: ${round(sell_price,2)} ({cfg.get('perc')}%)
📦 Stock ID: {pid[:8]}

⚡ Fast Buy - Limited Stock!
👇 Buy now from bot!
"""
                await context.bot.send_message(chat_id=STOCK_CHANNEL, text=new_stock_msg)
            except Exception as e:
                print(f"Channel error: {e}")

            await update.message.reply_text(f"✅ Stock Added + Channel Posted!\n🎁 {brand} ${amount}\nTotal Active: {len([p for p in products.values() if not p.get('sold')])}", reply_markup=admin_keyboard())
            context.user_data['wait']=None
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    data=q.data
    uid=q.from_user.id

    # BUYER BUY LOGIC - FIXED VENDOR SOLD BUG
    if data.startswith("buy_"):
        pid=data.replace("buy_","")
        products=load("products.json")
        if pid not in products:
            await q.edit_message_text("❌ Sold Out! Already sold.")
            return
        if products[pid].get('sold'):
            await q.edit_message_text("❌ Sold Out! This item is sold.")
            return

        orders=load("orders.json")
        # check duplicate pending
        for oid,o in orders.items():
            if o['product_id']==pid and o['buyer_id']==uid and o['status']=='pending':
                await q.edit_message_text("⏳ You already requested this! Wait for admin approval.")
                return

        oid=str(uuid.uuid4())
        orders[oid]={
            "buyer_id": uid,
            "buyer_username": f"@{q.from_user.username}" if q.from_user.username else q.from_user.first_name,
            "product_id": pid,
            "brand": products[pid]['brand'],
            "amount": products[pid]['amount'],
            "code": products[pid]['code'],
            "sell_price": products[pid]['sell_price'],
            "status": "pending"
        }
        save("orders.json", orders)
        await q.edit_message_text(f"✅ Request sent to Admin!\n\n🎁 {products[pid]['brand']} ${products[pid]['amount']}\nWait for approval.")
        try:
            admin_msg = f"🔔 NEW BUY REQUEST\n\n🆔 Order: {oid[:8]}\n👤 Buyer: {orders[oid]['buyer_username']} ID:{uid}\n🎁 {products[pid]['brand']} ${products[pid]['amount']}\nCode: {products[pid]['code']}"
            kb=[[InlineKeyboardButton("✅ Approve", callback_data=f"oapp_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"orej_{oid}")]]
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(kb))
        except: pass
        return

    # ADMIN ONLY
    if uid!=ADMIN_ID: return

    if data=="add_stock":
        context.user_data['wait']='add_stock'
        await q.edit_message_text("📦 Send: BRAND AMOUNT CODE\n\nEx: `Amazon 10 XYZ123ABC`\n\nDuplicate code auto-block!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_admin")]]), parse_mode='Markdown')

    elif data=="set_perc":
        context.user_data['wait']='set_perc'
        await q.edit_message_text("💲 Send % ex: 65", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_admin")]]))

    elif data=="add_balance":
        context.user_data['wait']='add_balance'
        await q.edit_message_text("💵 Send: USERID AMOUNT\nEx: 6699688350 10", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_admin")]]))

    elif data=="relist":
        products=load("products.json")
        active=[p for p in products.values() if not p.get('sold')]
        count=0
        for p in active[-10:]:
            try:
                msg=f"🎁 {p['brand']} ${p['amount']} - ${p['sell_price']}"
                await context.bot.send_message(chat_id=STOCK_CHANNEL, text=msg)
                count+=1
            except: pass
        await q.edit_message_text(f"🔄 {count} items relisted to channel!", reply_markup=admin_keyboard())

    elif data=="vendor_req":
        vendors=load("vendors.json")
        txt="🧑‍💼 Vendor Requests:\n\n"
        kb=[]
        pending=False
        for vid,v in vendors.items():
            if v.get('status')=='pending':
                pending=True
                txt+=f"ID: {vid} - {v.get('username')}\n"
                kb.append([InlineKeyboardButton(f"✅ Approve {vid}", callback_data=f"vapp_{vid}"), InlineKeyboardButton(f"❌ Reject", callback_data=f"vrej_{vid}")])
        if not pending: txt="No pending vendor requests"
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back_admin")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("vapp_"):
        vid=data.replace("vapp_","")
        vendors=load("vendors.json")
        if vid in vendors:
            vendors[vid]['status']='approved'
            save("vendors.json", vendors)
            await q.edit_message_text(f"✅ Vendor {vid} Approved!", reply_markup=admin_keyboard())
            try: await context.bot.send_message(chat_id=int(vid), text="✅ Your Vendor Request Approved! You can now sell.")
            except: pass

    elif data.startswith("vrej_"):
        vid=data.replace("vrej_","")
        vendors=load("vendors.json")
        if vid in vendors:
            vendors[vid]['status']='rejected'
            save("vendors.json", vendors)
            await q.edit_message_text(f"❌ Vendor {vid} Rejected", reply_markup=admin_keyboard())

    elif data=="all_sellers":
        vendors=load("vendors.json")
        txt="👥 All Sellers:\n\n"
        if not vendors: txt="No sellers yet"
        for vid,v in vendors.items():
            txt+=f"{vid} - {v.get('username','')} - {v.get('status')}\n"
        await q.edit_message_text(txt, reply_markup=admin_keyboard())

    elif data=="pending_orders":
        orders=load("orders.json")
        txt="⏳ Pending Orders:\n\n"
        kb=[]
        for oid,o in orders.items():
            if o.get('status')=='pending':
                txt+=f"🆔 {oid[:8]} | Buyer {o['buyer_id']} ({o['buyer_username']}) | {o['brand']} ${o['amount']}\n"
                kb.append([InlineKeyboardButton(f"✅ Approve {oid[:6]}", callback_data=f"oapp_{oid}"), InlineKeyboardButton(f"❌ Reject {oid[:6]}", callback_data=f"orej_{oid}")])
        if not kb: txt="No pending orders"
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="back_admin")])
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("oapp_"):
        oid=data.replace("oapp_","")
        orders=load("orders.json")
        if oid in orders:
            orders[oid]['status']='approved'
            save("orders.json", orders)
            sales=load("sales.json", [])
            sales.append(orders[oid])
            save("sales.json", sales)
            products=load("products.json")
            pid=orders[oid]['product_id']
            if pid in products:
                products[pid]['sold']=True
                save("products.json", products)

            await q.edit_message_text(f"✅ Order {oid[:8]} Approved & Buyer Notified!", reply_markup=admin_keyboard())

            # PREMIUM SOLD NOTIFY - STOCK CHANNEL
            try:
                sold_premium = f"""
╔════════════════════╗
    ❌ SOLD OUT ❌
╚════════════════════╝

🎁 Item: {orders[oid]['brand']} ${orders[oid]['amount']}
💲 Sold: ${orders[oid].get('sell_price')}
👤 Buyer: {orders[oid]['buyer_username']}
🆔 Order: {oid[:8]}

⚡ More stocks coming soon!
🔔 Stay tuned!
"""
                await context.bot.send_message(chat_id=STOCK_CHANNEL, text=sold_premium)
            except Exception as e:
                print(f"Sold notify error: {e}")

            try:
                await context.bot.send_message(chat_id=orders[oid]['buyer_id'], text=f"✅ Approved!\n\n🎁 {orders[oid]['brand']} ${orders[oid]['amount']}\n🔑 Code: `{orders[oid]['code']}`", parse_mode='Markdown')
            except: pass

    elif data.startswith("orej_"):
        oid=data.replace("orej_","")
        orders=load("orders.json")
        if oid in orders:
            orders[oid]['status']='rejected'
            save("orders.json", orders)
            await q.edit_message_text(f"❌ Order {oid[:8]} Rejected", reply_markup=admin_keyboard())
            try: await context.bot.send_message(chat_id=orders[oid]['buyer_id'], text="❌ Your order was rejected. Contact admin.")
            except: pass

    elif data=="sales_history":
        sales=load("sales.json", [])
        txt=f"📊 Sales History ({len(sales)}):\n\n"
        if not sales: txt="No sales yet"
        for s in sales[-20:]:
            txt+=f"{s.get('brand')} ${s.get('amount')} - {s.get('buyer_username')} - Approved\n"
        await q.edit_message_text(txt, reply_markup=admin_keyboard())

    elif data=="buyer_history":
        orders=load("orders.json")
        txt="📜 Buyer History:\n\n"
        if not orders: txt="No buyers yet"
        for o in list(orders.values())[-20:]:
            txt+=f"{o.get('buyer_id')} | {o.get('brand')} ${o.get('amount')} | {o.get('status')}\n"
        await q.edit_message_text(txt, reply_markup=admin_keyboard())

    elif data=="back_admin" or data=="back":
        await q.edit_message_text(admin_panel_text(), reply_markup=admin_keyboard())

def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot FULL FINAL with Premium SOLD UI started")
    app.run_polling()

if __name__=="__main__":
    main()
