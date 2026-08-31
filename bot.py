import os
import telebot
from telebot import types
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
LTC_ADDRESS = "LNDgqKM2CQ3LZved7z3mnbwBFdBQUbySZt"
SOL_ADDRESS = "DVvg75XKBCsXcuo1Wxe7A3BYcW3sXA5zcd76NLMHFxGy"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💳 My Balance"), types.KeyboardButton("👤 My Profile"),
        types.KeyboardButton("📋 Browse Cards"), types.KeyboardButton("🔍 Check Card"),
        types.KeyboardButton("💰 Deposit"), types.KeyboardButton("💸 Withdraw"),
        types.KeyboardButton("🎁 Refer & Earn"), types.KeyboardButton("🔑 Redeem Code"),
        types.KeyboardButton("⚙️ Filters"), types.KeyboardButton("📞 Support"),
        types.KeyboardButton("📜 Refund Rules"), types.KeyboardButton("💱 Exchange Rate")
    )
    bot.send_message(message.chat.id, f"Hi {message.from_user.first_name}! Welcome to Xprepaids Exchange ✅", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text and "Deposit" in m.text)
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("SOL Deposit", callback_data="dep_sol"),
        types.InlineKeyboardButton("LTC Deposit", callback_data="dep_ltc")
    )
    bot.send_message(message.chat.id, "💰 Choose your deposit method:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dep_"))
def deposit_callback(call):
    if call.data == "dep_sol":
        addr = SOL_ADDRESS
        coin = "SOL (Solana) Deposit"
        network = "Network: Solana (SPL)"
    else:
        addr = LTC_ADDRESS
        coin = "LTC (Litecoin) Deposit"
        network = "Network: Litecoin"
    
    text = f"""💰 {coin}

{network}
Address:
`{addr}`

💵 Minimum: $1 equivalent
⏳ No Pending Transactions

Send korar por TXID /check_deposit e din."""
    
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={addr}"
    bot.send_photo(call.message.chat.id, qr_url, caption=text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def others(message):
    if "/start" not in message.text:
        bot.send_message(message.chat.id, "Use /start for main menu")

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/")
def home():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    return "Bot Live with QR", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
