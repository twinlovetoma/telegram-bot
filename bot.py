import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRODUCTS = []
USERS_DB = {} # {user_id: {"purchases": [{"id, price, dt}], "deposits": [dt]}}

PER_PAGE = 5

def get_main(): return [p for p in PRODUCTS if 1 <= p['price'] <= 500]
def get_cents(): return [p for p in PRODUCTS if 0.10 <= p['price'] <= 0.98]

def build_keyboard(items, page, list_type):
    start = page * PER_PAGE
    slice_items = items[start:start+PER_PAGE]
    kb = []
    for p in slice_items:
        kb.append([InlineKeyboardButton(f"{p['name']} | ${p['price']}", callback_data=f"buy_{p['id']}")])

    nav = [
        InlineKeyboardButton("First", callback_data=f"{list_type}_0"),
        InlineKeyboardButton("-5", callback_data=f"{list_type}_{max(0,page-5)}"),
        InlineKeyboardButton("Back", callback_data=f"{list_type}_{max(0,page-1)}"),
        InlineKeyboardButton("Next", callback_data=f"{list_type}_{page+1}"),
        InlineKeyboardButton("+5", callback_data=f"{list_type}_{page+5}"),
        InlineKeyboardButton("Last", callback_data=f"{list_type}_last"),
    ]
    kb.append(nav)
    kb.append([InlineKeyboardButton("Refresh 🔄", callback_data=f"refresh_{list_type}_{page}"), InlineKeyboardButton("Purchase 🛒", callback_data="mypurchase")])
    if list_type == "main":
        kb.append([InlineKeyboardButton("Cents $0.10-$0.98 (Neche)", callback_data="cents_0")])
    return InlineKeyboardMarkup(kb)

async def listings(update, context):
    items = get_main()
    await update.message.reply_text(f"Listings $1-$500 | Total: {len(items)}", reply_markup=build_keyboard(items, 0, "main"))

async def cents_listing(update, context):
    items = get_cents()
    await update.message.reply_text(f"Cents $0.10-$0.98 | Total: {len(items)}", reply_markup=build_keyboard(items, 0, "cents"))

async def profile(update, context):
    user = update.effective_user
    u = USERS_DB.get(user.id, {"sol":0, "ltc":0, "usd":0, "deposits":[], "purchases":[]})
    last_deps = "\n".join(u['deposits'][-3:]) or "None"
    last_pur = "\n".join([f"ID {p['id']} | ${p['price']} | {p['dt']}" for p in u['purchases'][-3:]]) or "None"
    text = f"""⚡ X STOCK PROFILE ⚡
Name: {user.full_name}
Username: @{user.username}
User ID: {user.id}
SOL Balance: {u['sol']}
LTC Balance: {u['ltc']}
USD Total: ${u['usd']}

Deposits
- Last:
{last_deps}

Purchases
- Count: {len(u['purchases'])}
- Last (with DateTime):
{last_pur}
"""
    await update.message.reply_text(text)

async def button_handler(update, context):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    if user_id not in USERS_DB: USERS_DB[user_id] = {"sol":0,"ltc":0,"usd":0,"deposits":[],"purchases":[]}

    data = q.data
    if data.startswith("buy_"):
        pid = int(data.split("_")[1])
        p = next((x for x in PRODUCTS if x['id']==pid), None)
        if p:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            USERS_DB[user_id]["purchases"].append({"id":pid, "price":p['price'], "dt":now})
            await q.message.reply_text(f"Purchased: {p['name']} | ${p['price']} | {now}")
    elif "main" in data or "cents" in data:
        list_type = "main" if "main" in data else "cents"
        items = get_main() if list_type=="main" else get_cents()
        page = 0 if "last" not in data else max(0, len(items)//PER_PAGE -1)
        try: page = int(data.split("_")[-1]) if "last" not in data and "refresh" not in data else page
        except: page=0
        await q.edit_message_text(f"{list_type} | Page {page}", reply_markup=build_keyboard(items, page, list_type))

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("listings", listings))
app.add_handler(CommandHandler("cents_listing", cents_listing))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(CommandHandler("add_product", lambda u,c: c.bot.send_message(u.effective_chat.id, "Use: /add_product Name | 12.5 | InStock")))
app.add_handler(CallbackQueryHandler(button_handler))
app.run_polling()
