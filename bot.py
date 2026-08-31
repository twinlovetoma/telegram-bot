import os
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    text = f"Hi {name}! Welcome to Xprepaids Exchange ✅\nSelect option:"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💳 My Balance"), types.KeyboardButton("👤 My Profile"),
        types.KeyboardButton("📋 Browse Cards"), types.KeyboardButton("🔍 Check Card"),
        types.KeyboardButton("💰 Deposit"), types.KeyboardButton("💸 Withdraw"),
        types.KeyboardButton("🎁 Refer & Earn"), types.KeyboardButton("🔑 Redeem Code"),
        types.KeyboardButton("⚙️ Filters"), types.KeyboardButton("📞 Support"),
        types.KeyboardButton("📜 Refund Rules"), types.KeyboardButton("💱 Exchange Rate")
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def all_buttons(message):
    txt = message.text
    if "Balance" in txt:
        bot.send_message(message.chat.id, "💳 Your Balance: $0.00\nUse /balance")
    elif "Deposit" in txt:
        bot.send_message(message.chat.id, "💰 Deposit:\nSend /deposit to get SOL/LTC address with QR.\nAuto verify enabled ✅")
    elif "Withdraw" in txt:
        bot.send_message(message.chat.id, "💸 Withdraw:\nUse /withdraw AMOUNT ADDRESS")
    elif "Profile" in txt:
        bot.send_message(message.chat.id, f"👤 ID: {message.from_user.id}\nName: {message.from_user.first_name}")
    elif "Browse" in txt:
        bot.send_message(message.chat.id, "📋 /listings command e chap din")
    elif "Filters" in txt:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.KeyboardButton("Unregistered"), types.KeyboardButton("Cents <$0.99"))
        bot.send_message(message.chat.id, "⚙️ Filters: /unregistered_listing, /cents_listing, /listing_filter, /listing_range")
    else:
        bot.send_message(message.chat.id, "Menu theke select koro or /start dao")

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/")
def home():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    return "Bot Live Full Menu", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
