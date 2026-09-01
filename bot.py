import os, json, hashlib, re, time, threading, io
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
SOL_PRICE = 150.0
LTC_PRICE = 48.88
MIN_SOL = 0.1
MIN_LTC = 0.05

def load(f):
    try:
        with open(f,"r") as fp: return json.load(fp)
    except: return {} if any(x in f for x in ["deposit","pending","filter","users","products","settings","sold","refund","trans"]) else [] if "sales" in f else {}
def save(f,d):
    with open(f,"w") as fp: json.dump(d, fp, indent=2)

def get_user(uid, users):
    if uid not in users:
        users[uid] = {"balance":0.0, "sol":0.0, "ltc":0.0, "is_seller":False}
    for k in ["sol","ltc","balance","is_seller"]:
        if k not in users[uid]:
            users[uid][k] = 0.0 if k!="is_seller" else False
    return users[uid]

def balance_text(user):
    sol_usd = user.get("sol",0)*SOL_PRICE
    ltc_usd = user.get("ltc",0)*LTC_PRICE
    total = user.get("balance",0) + sol_usd + ltc_usd
    if user.get("sol",0)==0 and user.get("ltc",0)==0:
        total = user.get("balance",0)
    txt = f"💰 *Balance:*\n💵 USD: *${total:.2f}*\n• SOL: `{user.get('sol',0):.10f}` (${sol_usd:.2f})\n• LTC: `{user.get('ltc',0):.10f}` (${ltc_usd:.2f})"
    return txt, total

def make_qr(address):
    if not qrcode or not address or "Not Set" in address:
        return None
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(address)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

def main_menu(uid, is_admin=False, is_seller=False):
    kb=[
        [InlineKeyboardButton("🛒 SHOP NOW", callback_data="browse")],
        [InlineKeyboardButton("💳 Balance", callback_data="bal"), InlineKeyboardButton("💵 Deposit", callback_data="dep")],
        [InlineKeyboardButton("👤 Profile", callback_data="prof")],
    ]
    if is_seller: kb.append([InlineKeyboardButton("🏪 SELLER DASHBOARD", callback_data="seller_dash")])
    if is_admin:
        kb.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin")])
        if not is_seller: kb.append([InlineKeyboardButton("🏪 SELLER DASHBOARD", callback_data="seller_dash")])
    return kb

def shop_bottom_bar():
    return [
        [InlineKeyboardButton("⚙️ Filters", callback_data="filters"), InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
        [InlineKeyboardButton("💰 Deposit", callback_data="dep"), InlineKeyboardButton("🔄 Refresh", callback_data="browse")]
    ]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users=load("users.json"); uid=str(update.effective_user.id)
    user=get_user(uid, users); save("users.json",users)
    is_admin=int(uid)==ADMIN; is_seller=user.get("is_seller", False)
    bal_txt, _ = balance_text(user)
    text=f"✨ *PREMIUM STORE* ✨\n━━━━━━━━━━━━\n{bal_txt}\n━━━━━━━━━━━━"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(main_menu(uid, is_admin, is_seller)))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); d=q.data; uid=str(q.from_user.id)
    users=load("users.json"); products=load("products.json"); settings=load("settings.json")
    if not settings: settings={"perc":65}
    user=get_user(uid, users); save("users.json",users)
    is_admin=q.from_user.id==ADMIN; is_seller=user.get("is_seller", False)

    # BROWSE + FILTERS
    if d=="browse" or d.startswith("filter_"):
        if d.startswith("filter_"):
            context.user_data['filter'] = d
        user_filter = context.user_data.get('filter', 'filter_all')
        all_products = list(products.items())
        if not all_products:
            kb = [[InlineKeyboardButton("🏠 Main Menu", callback_data="back")], [InlineKeyboardButton("🔄 Refresh", callback_data="browse")]]
            await q.edit_message_text("😔 *No Stock*\nRefresh after sometime", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            return
        filtered = all_products
        if user_filter == "filter_low": filtered = sorted(all_products, key=lambda x: x[1]['sell_price'])
        elif user_filter == "filter_high": filtered = sorted(all_products, key=lambda x: x[1]['sell_price'], reverse=True)
        elif user_filter == "filter_under5": filtered = [x for x in all_products if x[1]['sell_price'] < 5]
        elif user_filter == "filter_5_10": filtered = [x for x in all_products if 5 <= x[1]['sell_price'] <= 10]
        elif user_filter == "filter_above10": filtered = [x for x in all_products if x[1]['sell_price'] > 10]
        if not filtered:
            txt = f"😔 *No items for filter `{user_filter}`*"
            kb = [[InlineKeyboardButton("⚙️ Filters", callback_data="filters")], [InlineKeyboardButton("🔙 Back to Shop", callback_data="browse")]]
            kb.extend(shop_bottom_bar())
            await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            return
        txt=f"🔥 *LATEST STOCK* 🔥\n━━━━━━━━━━━━\n📦 Total: *{len(filtered)}* | Filter: *{user_filter.replace('filter_','').upper()}*\n━━━━━━━━━━━━\n\n"
        kb=[]
        for i,(pid,p) in enumerate(filtered[:15],1):
            txt+=f"`{i}.` *{p.get('first4','CODE')}**** |* `${p['sell_price']}` `(MRP ${p['amount']})`\n"
            kb.append([InlineKeyboardButton(f"🛒 Purchase - {p.get('first4')}****", callback_data=f"buy_{pid}")])
        kb.extend(shop_bottom_bar())
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d=="filters":
        kb=[
            [InlineKeyboardButton("💲 Low to High", callback_data="filter_low"), InlineKeyboardButton("💲 High to Low", callback_data="filter_high")],
            [InlineKeyboardButton("📉 Under $5", callback_data="filter_under5"), InlineKeyboardButton("📊 $5 - $10", callback_data="filter_5_10")],
            [InlineKeyboardButton("📈 Above $10", callback_data="filter_above10"), InlineKeyboardButton("🔄 All Items", callback_data="filter_all")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back"), InlineKeyboardButton("🔙 Back to Shop", callback_data="browse")]
        ]
        txt="⚙️ *FILTERS*\n━━━━━━━━━━━━\n• Low to High\n• High to Low\n• Under $5\n• $5-$10\n• Above $10\n━━━━━━━━━━━━"
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d=="back":
        bal_txt, _ = balance_text(user)
        await q.edit_message_text(f"🏠 *MAIN MENU*\n━━━━━━━━━━━━\n{bal_txt}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(main_menu(uid, is_admin, is_seller)))
        return

    elif d=="bal":
        bal_txt,_=balance_text(user)
        kb = [[InlineKeyboardButton("💰 Deposit", callback_data="dep"), InlineKeyboardButton("🛒 Shop", callback_data="browse")], [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]]
        await q.edit_message_text(bal_txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d=="dep":
        kb=[[InlineKeyboardButton("🟣 Deposit SOL", callback_data="dep_sol"), InlineKeyboardButton("🔵 Deposit LTC", callback_data="dep_ltc")], [InlineKeyboardButton("⚙️ Filters", callback_data="filters"), InlineKeyboardButton("🏠 Main Menu", callback_data="back")], [InlineKeyboardButton("🛒 Shop", callback_data="browse"), InlineKeyboardButton("🔄 Refresh", callback_data="dep")]]
        bal_txt,_=balance_text(user)
        await q.edit_message_text(f"💵 *DEPOSIT*\n━━━━━━━━━━━━\n{bal_txt}\n━━━━━━━━━━━━\n👇 Select coin", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d in ["dep_sol","dep_ltc"]:
        coin="SOL" if d=="dep_sol" else "LTC"
        min_amt=MIN_SOL if coin=="SOL" else MIN_LTC
        addr_key="sol_deposit" if coin=="SOL" else "ltc_deposit"
        addr=settings.get(addr_key,"Not Set - Contact Admin")
        if "Not Set" in addr:
            await q.edit_message_text(f"❌ {coin} Address Not Set\nAdmin Panel -> Set SOL/LTC Address", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="dep")]]))
            return
        dep_reqs=load("deposit_requests.json")
        req_id=hashlib.md5(f"{uid}{coin}{time.time()}".encode()).hexdigest()[:6]
        expire_at=datetime.now()+timedelta(minutes=30)
        dep_reqs[req_id]={"uid":uid,"coin":coin,"addr":addr,"min":min_amt,"expire":expire_at.strftime("%Y-%m-%d %H:%M:%S"),"time":time.strftime("%H:%M"),"status":"waiting_deposit","txid":None}
        save("deposit_requests.json",dep_reqs)
        emoji="🟣" if coin=="SOL" else "🔵"
        txt=(
            f"{emoji} *{coin} DEPOSIT - QR READY* {emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Request: `#{req_id}`\n"
            f"📥 Address:\n`{addr}`\n\n"
            f"💰 Minimum: `{min_amt} {coin}`\n"
            f"⏰ Expires: *30 Minutes* ({expire_at.strftime('%H:%M:%S')})\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *WARNING:*\n"
            f"• Only {coin} to this address\n"
            f"• Less than {min_amt} = NOT added\n"
            f"• Wrong coin = LOST\n"
        )
        kb=[
            [InlineKeyboardButton(f"📋 Copy {coin} Address", callback_data=f"copy_{coin.lower()}")],
            [InlineKeyboardButton("📝 Submit TXID", callback_data=f"submit_txid_{req_id}")],
            [InlineKeyboardButton("⚙️ Filters", callback_data="filters"), InlineKeyboardButton("🏠 Main Menu", callback_data="back")],
            [InlineKeyboardButton("💰 Deposit", callback_data="dep"), InlineKeyboardButton("🔄 Refresh", callback_data="browse")]
        ]
        qr_bio = make_qr(addr)
        if qr_bio:
            try: await q.message.delete()
            except: pass
            await context.bot.send_photo(chat_id=q.message.chat_id, photo=qr_bio, caption=txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d.startswith("copy_"):
        coin=d.split("copy_")[1].upper()
        key="sol_deposit" if coin=="SOL" else "ltc_deposit"
        await q.answer(f"{coin} Copied: {settings.get(key,'Not Set')}", show_alert=True)
        return

    elif d.startswith("submit_txid_"):
        req_id=d.split("submit_txid_")[1]
        context.user_data['w']=f'txid_{req_id}'
        dep_reqs=load("deposit_requests.json")
        if req_id not in dep_reqs:
            await q.edit_message_text("❌ Request expired", reply_markup=InlineKeyboardMarkup(shop_bottom_bar())); return
        try:
            exp=datetime.strptime(dep_reqs[req_id]['expire'], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp:
                await q.edit_message_text(f"❌ Request #{req_id} EXPIRED\nCreate new deposit", reply_markup=InlineKeyboardMarkup(shop_bottom_bar())); return
        except: pass
        await q.edit_message_text(f"📝 *SUBMIT TXID for #{req_id}*\n\nSend TXID now", parse_mode="Markdown")
        return

    elif d=="prof":
        bal_txt,_=balance_text(user)
        txt=f"👤 *PROFILE*\n🆔 `{uid}`\n{bal_txt}\n🏪 {'Seller ✅' if is_seller else 'Not Seller ❌'}"
        kb=[[InlineKeyboardButton("🏠 Main Menu", callback_data="back")]]
        if is_seller: kb.append([InlineKeyboardButton("🏪 Seller Dashboard", callback_data="seller_dash")])
        if is_admin: kb.append([InlineKeyboardButton("👑 Admin", callback_data="admin")])
        if not is_seller: kb.append([InlineKeyboardButton("🏪 Become Seller", callback_data="apply_vendor")])
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d=="admin" and is_admin:
        kb=[
            [InlineKeyboardButton("➕ Add Stock", callback_data="add")],
            [InlineKeyboardButton("💲 Set %", callback_data="setp"), InlineKeyboardButton("💵 Add Balance", callback_data="ab")],
            [InlineKeyboardButton("💳 Set SOL/LTC Address", callback_data="set_deposit")],
            [InlineKeyboardButton("💰 Deposit Requests", callback_data="dep_reqs"), InlineKeyboardButton("⚠️ Refund Requests", callback_data="refund_reqs")],
            [InlineKeyboardButton("⏳ Pending Orders", callback_data="pending"), InlineKeyboardButton("🔄 Relist", callback_data="relist")],
            [InlineKeyboardButton("🏪 Vendor Req", callback_data="vendors"), InlineKeyboardButton("👥 Sellers", callback_data="allsellers")],
            [InlineKeyboardButton("📊 Sales", callback_data="sales")],
            [InlineKeyboardButton("🏪 Seller Dashboard", callback_data="seller_dash")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="back")]
        ]
        await q.edit_message_text(f"👑 *ADMIN PANEL*\nStock:{len(products)}\nSOL: `{settings.get('sol_deposit','Not Set')}`\nLTC: `{settings.get('ltc_deposit','Not Set')}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d=="set_deposit" and is_admin:
        kb=[[InlineKeyboardButton("🟣 Set SOL Address", callback_data="set_sol_addr")],[InlineKeyboardButton("🔵 Set LTC Address", callback_data="set_ltc_addr")],[InlineKeyboardButton("🔙 Back", callback_data="admin")]]
        await q.edit_message_text(f"💳 *SET DEPOSIT ADDRESS*\n\nSOL ({MIN_SOL} min): `{settings.get('sol_deposit','Not Set')}`\nLTC ({MIN_LTC} min): `{settings.get('ltc_deposit','Not Set')}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d=="set_sol_addr" and is_admin:
        context.user_data['w']='set_sol_addr'; await q.edit_message_text(f"🟣 Send new SOL Address\nMin {MIN_SOL} SOL"); return
    elif d=="set_ltc_addr" and is_admin:
        context.user_data['w']='set_ltc_addr'; await q.edit_message_text(f"🔵 Send new LTC Address\nMin {MIN_LTC} LTC"); return

    elif d=="dep_reqs" and is_admin:
        dep_reqs=load("deposit_requests.json")
        if not dep_reqs:
            await q.edit_message_text("No deposit requests", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin")]])); return
        txt="💰 *DEPOSIT REQUESTS*\n━━━━━━━━━━━━\n"; kb=[]
        for rid,r in list(dep_reqs.items())[-10:][::-1]:
            try:
                exp=datetime.strptime(r['expire'], "%Y-%m-%d %H:%M:%S")
                status="✅ ACTIVE" if datetime.now()<=exp else "❌ EXPIRED"
            except: status=r.get('status','')
            txid=r.get('txid','No TXID')
            if len(txid)>20: txid=txid[:20]+"..."
            txt+=f"#{rid} {r['coin']} U:`{r['uid']}` {status}\nTX: {txid}\n---\n"
            if r.get('txid'):
                kb.append([InlineKeyboardButton(f"✅ Approve {rid}", callback_data=f"dep_apv_{rid}"), InlineKeyboardButton(f"❌ Reject {rid}", callback_data=f"dep_rej_{rid}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d.startswith("dep_apv_") and is_admin:
        rid=d.split("dep_apv_")[1]; dep_reqs=load("deposit_requests.json"); users=load("users.json")
        if rid not in dep_reqs: return
        r=dep_reqs[rid]
        uid2=r['uid']; coin=r['coin']; min_amt=r['min']
        u=get_user(uid2, users)
        if coin=="SOL": u["sol"]=u.get("sol",0)+min_amt
        else: u["ltc"]=u.get("ltc",0)+min_amt
        save("users.json",users)
        del dep_reqs[rid]; save("deposit_requests.json",dep_reqs)
        await q.edit_message_text(f"✅ Approved #{rid}\nAdded {min_amt} {coin} to {uid2}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin")]]))
        try: await context.bot.send_message(chat_id=int(uid2), text=f"✅ Deposit Approved #{rid}\nAdded {min_amt} {coin}", parse_mode="Markdown")
        except: pass
        return

    elif d.startswith("dep_rej_") and is_admin:
        rid=d.split("dep_rej_")[1]; dep_reqs=load("deposit_requests.json")
        if rid in dep_reqs: del dep_reqs[rid]; save("deposit_requests.json",dep_reqs)
        await q.edit_message_text(f"❌ Rejected #{rid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin")]]))
        return

    # ===== REFUND REQUESTS ADMIN =====
    elif d=="refund_reqs" and is_admin:
        refunds=load("refund_requests.json")
        if not refunds:
            await q.edit_message_text("No refund requests", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin")]])); return
        txt="⚠️ *REFUND REQUESTS - FULL DETAILS*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        kb=[]
        for rid,r in list(refunds.items())[-10:][::-1]:
            txt+=f"🆔 Refund `#{rid}`\n"
            txt+=f"👤 Buyer: `{r['buyer']}`\n"
            txt+=f"🏪 Seller: `{r['seller']}`\n"
            txt+=f"🔑 Code: `{r['code'][:30]}...`\n"
            txt+=f"💰 Balance: ${r['amount']} Sold: ${r['sell_price']}\n"
            txt+=f"📅 Purchase: {r['purchase_time']}\n"
            txt+=f"🆔 Purchase ID: `{r['purchase_id']}`\n"
            txt+=f"📝 Reason: {r.get('reason','No reason')}\n"
            txt+=f"⏰ Requested: {r['request_time']}\n"
            txt+=f"━━━━━━━━━━━━\n"
            kb.append([InlineKeyboardButton(f"✅ Approve Refund {rid}", callback_data=f"ref_apv_{rid}"), InlineKeyboardButton(f"❌ Reject {rid}", callback_data=f"ref_rej_{rid}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin")])
        await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    elif d.startswith("ref_apv_") and is_admin:
        rid=d.split("ref_apv_")[1]; refunds=load("refund_requests.json"); users=load("users.json")
        if rid not in refunds: return
        r=refunds[rid]
        buyer=r['buyer']
        b_user=get_user(buyer, users)
        b_user["balance"]=b_user.get("balance",0)+float(r['sell_price'])
        save("users.json",users)
        del refunds[rid]; save("refund_requests.json",refunds)
        await q.edit_message_text(f"✅ Refund Approved #{rid}\nRefunded ${r['sell_price']} to {buyer}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin")]]))
        try: await context.bot.send_message(chat_id=int(buyer), text=f"✅ *Refund Approved* #{rid}\n\n💰 ${r['sell_price']} added to balance\nCode: `{r['purchase_id']}`", parse_mode="Markdown")
        except: pass
        return

    elif d.startswith("ref_rej_") and is_admin:
        rid=d.split("ref_rej_")[1]; refunds=load("refund_requests.json")
        if rid in refunds:
            buyer=refunds[rid]['buyer']
            del refunds[rid]; save("refund_requests.json",refunds)
            await q.edit_message_text(f"❌ Refund Rejected #{rid}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin")]]))
            try: await context.bot.send_message(chat_id=int(buyer), text=f"❌ Refund #{rid} rejected by admin")
            except: pass
        return

    elif d=="seller_dash" and (is_seller or is_admin):
        my_products = {pid:p for pid,p in products.items() if p.get("seller_id")==uid}
        bal_txt,_=balance_text(user)
        txt=f"🏪 *SELLER DASHBOARD*\n━━━━━━━━━━━━\n{bal_txt}\n📦 My AVL: *{len(my_products)}*\n💸 95% 
