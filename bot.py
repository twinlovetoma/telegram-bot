import os, json, hashlib, re, time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN = int(os.getenv("ADMIN_ID", "0"))
SELLER_FEE = 20
RESELL_FEE = 5

def load(f):
    try:
        if not os.path.exists(f): return {}
        with open(f,"r") as fp: return json.load(fp)
    except: return {}
def save(f,d):
    with open(f,"w") as fp: json.dump(d, fp, indent=2)

def parse_gift(text):
    m=re.search(r'\$\s*(\d+(?:\.\d+)?)', text)
    if not m: raise ValueError("Format: Details $Price\nEx: CODM 420 CP $5")
    amount=float(m.group(1))
    details=text.split('$')[0].strip()
    if len(details)<3: raise ValueError("Short details")
    words=details.split()
    brand=words[0].upper()
    if len(words)>1 and words[0].lower() in ['call','free','pubg','mobile','cod','garena','codm']:
        brand=" ".join(words[:2]).upper()
    h=hashlib.sha256(details.lower().encode()).hexdigest()
    return brand[:20], details, amount, h

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json")
    uid=str(update.effective_user.id)
    if uid not in users:
        users[uid]={"balance":0,"is_seller":False,"can_resell":False,"sales":0,"joined":time.time()}
        save("users.json",users)
    kb=[
        [InlineKeyboardButton("🔥 Latest Items", callback_data="browse")],
        [InlineKeyboardButton("🎮 CODM"), InlineKeyboardButton("🔥 Free Fire"), InlineKeyboardButton("PUBG")],
        [InlineKeyboardButton("👤 My Profile"), InlineKeyboardButton("🏪 Vendor Panel")],
        [InlineKeyboardButton("💵 Deposit"), InlineKeyboardButton("📜 My Orders")]
    ]
    await update.message.reply_text(f"🎮 **Welcome to Game Top-Up Shop**\n\nHi {update.effective_user.first_name}!\n\nCODM / Free Fire / PUBG / All Gifts", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    uid=str(q.from_user.id); uid_int=q.from_user.id
    users=load("users.json"); products=load("products.json"); settings=load("settings.json")
    if not isinstance(settings, dict): settings={"global_perc":65,"global_fixed":None}
    if uid not in users: users[uid]={"balance":0,"is_seller":False,"can_resell":False,"sales":0}; save("users.json",users)

    # BROWSE
    if q.data=="browse" or q.data in ["CODM","FREE","PUBG"]:
        filt=q.data
        items=list(products.items())
        if filt!="browse":
            items=[(k,v) for k,v in items if filt in v['brand']]
        if not items:
            await q.edit_message_text("No items in this category", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]])); return
        t=f"🔥 {filt} - {len(items)} items\n\n"; kb=[]
        for pid,p in items[:15]:
            t+=f"• {p['brand']} | ${p['amount']} → **${p['sell_price']}**\n"
            kb.append([InlineKeyboardButton(f"Buy {p['brand']} ${p['sell_price']}", callback_data=f"buy_{pid}")])
        kb.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="back")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif q.data.startswith("buy_"):
        pid=q.data.split("buy_")[1]
        p=products.get(pid)
        if not p: await q.edit_message_text("Sold out"); return
        kb=[[InlineKeyboardButton(f"✅ Confirm Pay ${p['sell_price']}", callback_data=f"confirm_{pid}")],[InlineKeyboardButton("⬅️ Back", callback_data="browse")]]
        await q.edit_message_text(f"📦 **{p['brand']}**\n\nDetails: `{p['code']}`\nMRP: ${p['amount']}\n**Sell: ${p['sell_price']}**\n\nBalance: ${users[uid]['balance']}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif q.data.startswith("confirm_"):
        pid=q.data.split("confirm_")[1]; p=products.get(pid)
        if not p: return
        if users[uid]["balance"] < float(p["sell_price"]):
            await q.edit_message_text(f"❌ Low Balance ${users[uid]['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💵 Deposit", callback_data="deposit")]])); return
        users[uid]["balance"]-=float(p["sell_price"])
        orders=load("orders.json"); orders[pid]={"buyer":uid,"product":p,"time":time.time()}; save("orders.json",orders)
        seller_id=p.get("seller_id")
        if seller_id and seller_id in users:
            users[seller_id]["balance"]=users[seller_id].get("balance",0)+float(p["sell_price"])*0.9 # seller gets 90%
            users[seller_id]["sales"]=users[seller_id].get("sales",0)+1
        save("users.json",users)
        del products[pid]; save("products.json",products)
        await q.edit_message_text(f"✅ **Delivered!**\n\n`{p['code']}`\n\nSave this. Check My Orders.", parse_mode="Markdown")

    elif q.data=="profile":
        u=users[uid]
        t=f"👤 **Profile**\nID: `{uid}`\n💰 Balance: ${u['balance']}\n🏪 Seller: {u['is_seller']}\n♻️ Resell: {u['can_resell']}\n📦 Sales: {u.get('sales',0)}"
        kb=[[InlineKeyboardButton("🏪 Vendor"),InlineKeyboardButton("💵 Deposit")],[InlineKeyboardButton("📜 My Orders"),InlineKeyboardButton("🔥 Shop")]]
        if uid_int==ADMIN: kb.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif q.data=="vendor":
        u=users[uid]
        if not u.get("is_seller"):
            await q.edit_message_text(f"🏪 **Vendor Locked**\n\nFee ${SELLER_FEE} to unlock add item\nYour: ${u['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"Buy Vendor ${SELLER_FEE}", callback_data="buy_seller")],[InlineKeyboardButton("Back", callback_data="profile")]])); return
        my={k:v for k,v in products.items() if v.get('seller_id')==uid}
        t=f"🏪 **Dashboard**\nItems: {len(my)}\nPerc: {settings.get('global_perc',65)}%\n\n"
        kb=[]
        for pid,p in my.items():
            kb.append([InlineKeyboardButton(f"{p['brand']} ${p['sell_price']}", callback_data="noop"), InlineKeyboardButton("➖", callback_data=f"p_down_{pid}"), InlineKeyboardButton("➕", callback_data=f"p_up_{pid}"), InlineKeyboardButton("❌", callback_data=f"del_{pid}")])
        kb.append([InlineKeyboardButton("➕ Add New Item", callback_data="a_add")])
        if not u.get("can_resell"): kb.append([InlineKeyboardButton(f"♻️ Buy Resell ${RESELL_FEE}", callback_data="buy_resell")])
        kb.append([InlineKeyboardButton("⬅️ Back", callback_data="profile")])
        await q.edit_message_text(t, reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="buy_seller":
        if users[uid]["balance"]<SELLER_FEE: await q.edit_message_text("Low balance"); return
        users[uid]["balance"]-=SELLER_FEE; users[uid]["is_seller"]=True; save("users.json",users)
        await q.edit_message_text("✅ Vendor Enabled", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Dashboard", callback_data="vendor")]]))
    elif q.data=="buy_resell":
        if users[uid]["balance"]<RESELL_FEE: await q.edit_message_text("Low balance"); return
        users[uid]["balance"]-=RESELL_FEE; users[uid]["can_resell"]=True; save("users.json",users)
        await q.edit_message_text("✅ Resell Enabled")

    elif q.data=="deposit":
        await q.edit_message_text(f"💵 **Deposit**\n\nID: `{uid}`\nMin $5\n\nAdmin ke Bkash/Nagad e taka diye ID dao\nAuto add hoye jabe", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="profile")]]))

    elif q.data=="admin":
        if uid_int!=ADMIN: return
        perc=settings.get("global_perc",65); fixed=settings.get("global_fixed")
        kb=[
            [InlineKeyboardButton("📋 All Stock List", callback_data="a_list")],
            [InlineKeyboardButton(f"💲 Set % ({perc}%)", callback_data="set_all_price"), InlineKeyboardButton(f"💲 Fixed ${fixed if fixed else 'OFF'}", callback_data="set_fixed")],
            [InlineKeyboardButton("💵 Add Bal"), InlineKeyboardButton("💸 Release Bal")],
            [InlineKeyboardButton("📢 Broadcast"), InlineKeyboardButton("👥 Users")],
            [InlineKeyboardButton("🗑️ Delete All Stock", callback_data="del_all")],
            [InlineKeyboardButton("⬅️ Back", callback_data="profile")]
        ]
        await q.edit_message_text(f"👑 **Admin**\nGlobal %: {perc}%\nFixed: {fixed}\nItems: {len(products)}\nUsers: {len(users)}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif q.data.startswith("p_"):
        if not users[uid].get("is_seller") and uid_int!=ADMIN: return
        _, act, pid = q.data.split("_",2)
        if pid not in products: return
        if act=="down": products[pid]["sell_price"]=round(max(0.1,float(products[pid]["sell_price"])-0.5),2)
        if act=="up": products[pid]["sell_price"]=round(float(products[pid]["sell_price"])+0.5,2)
        save("products.json",products); await q.answer(f"Now ${products[pid]['sell_price']}")

    elif q.data=="a_list":
        if uid_int!=ADMIN: return
        t="📋 All Stock\n"; kb=[]
        for pid,p in products.items():
            t+=f"{pid[:5]} {p['brand']} ${p['amount']}->{p['sell_price']} by {p.get('seller_id','?')}\n"
            kb.append([InlineKeyboardButton(f"Del {p['brand']}", callback_data=f"del_{pid}")])
        kb.append([InlineKeyboardButton("Back", callback_data="admin")])
        await q.edit_message_text(t[:4000], reply_markup=InlineKeyboardMarkup(kb))

    elif q.data=="set_all_price":
        if uid_int!=ADMIN: return
        context.user_data['w']='set_all_price'
        await q.edit_message_text("💲 % dao\nEx: 50 = $10 -> $5\nEx: 70 = $10 -> $7\nEx: 39 = $10 -> $3.9")
    elif q.data=="set_fixed":
        if uid_int!=ADMIN: return
        context.user_data['w']='set_fixed'
        await q.edit_message_text("💲 Fixed price dao sob item er jonno\nEx: 2 = sob $2\nOFF korte 0 likho")

    elif q.data.startswith("del_"):
        pid=q.data.split("del_")[1]
        if pid in products: del products[pid]; save("products.json",products)
        await q.answer("Deleted"); await q.edit_message_text("Deleted", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="admin")]]))

    elif q.data=="del_all":
        if uid_int!=ADMIN: return
        save("products.json",{}); await q.edit_message_text("All deleted")
    elif q.data=="back":
        kb=[[InlineKeyboardButton("🔥 Latest", callback_data="browse")],[InlineKeyboardButton("👤 Profile"),InlineKeyboardButton("🏪 Vendor")]]
        await q.edit_message_text("Main Menu", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data=="a_add":
        context.user_data['w']='add_gift'
        await q.edit_message_text("📩 Details $Price\nEx: `CODM 420 CP $5`\n`Free Fire 100 DIA UID 123 $3`", parse_mode="Markdown")

async def mh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt=update.message.text.strip(); w=context.user_data.get('w')
    users=load("users.json"); products=load("products.json"); settings=load("settings.json")
    if not isinstance(settings, dict): settings={"global_perc":65,"global_fixed":None}
    uid=str(update.effective_user.id)

    if w=='set_all_price':
        try:
            perc=float(txt.replace('%','').strip())
            settings["global_perc"]=perc; settings["global_fixed"]=None
            for pid in products: products[pid]["sell_price"]=round(float(products[pid]["amount"])*perc/100,2)
            save("products.json",products); save("settings.json",settings)
            await update.message.reply_text(f"✅ All {len(products)} items now {perc}%\n$10->{round(10*perc/100,2)}")
        except: await update.message.reply_text("Valid % dao")
        context.user_data['w']=None; return

    if w=='set_fixed':
        try:
            fp=float(txt.replace('$','').strip())
            if fp==0: settings["global_fixed"]=None; await update.message.reply_text("Fixed OFF, % mode on")
            else:
                settings["global_fixed"]=fp
                for pid in products: products[pid]["sell_price"]=fp
                await update.message.reply_text(f"✅ All fixed ${fp}")
            save("products.json",products); save("settings.json",settings)
        except: await update.message.reply_text("Number dao")
        context.user_data['w']=None; return

    if w=='add_gift':
        try:
            brand, code, amount, h = parse_gift(txt)
            for p in products.values():
                if p.get("hash")==h: await update.message.reply_text("Duplicate"); context.user_data['w']=None; return
            fixed=settings.get("global_fixed"); perc=float(settings.get("global_perc",65))
            final_price=round(float(fixed),2) if fixed else round(amount*perc/100,2)
            pid=hashlib.md5(f"{uid}{code}{time.time()}".encode()).hexdigest()[:10]
            products[pid]={"brand":brand,"code":code,"amount":amount,"sell_price":final_price,"seller_id":uid,"hash":h}
            save("products.json",products)
            await update.message.reply_text(f"✅ Added {brand} ${amount}->{final_price} ({perc if not fixed else f'Fixed ${fixed}'})")
        except Exception as e: await update.message.reply_text(f"❌ {e}")
        context.user_data['w']=None; return

    if w=='bal':
        try:
            tid, amt = txt.split(); users[tid]["balance"]+=float(amt); save("users.json",users); await update.message.reply_text("Added")
        except: await update.message.reply_text("Format: ID AMT")
        context.user_data['w']=None; return

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mh))
    app.run_polling()
if __name__=="__main__": main()
