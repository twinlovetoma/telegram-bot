import os, math
import telebot
from telebot import types
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
LTC_ADDRESS = "LNDgqKM2CQ3LZved7z3mnbwBFdBQUbySZt"
SOL_ADDRESS = "DVvg75XKBCsXcuo1Wxe7A3BYcW3sXA5zcd76NLMHFxGy"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

MY_BALANCE = 8.22
MY_CARDS = [
    "533985xx CAD212.36 at 39%",
    "403446xx USD118.43 at 39%",
    "435880xx USD100.00 at 39%",
    "435880xx USD99.16 at 39%",
]

def get_text(page):
    total = math.ceil(len(MY_CARDS)/10)
    s = page*10
    txt = ""
    for i, c in enumerate(MY_CARDS[s:s+10], start=s+1):
        txt += f"{i}. {c}\n"
    return f"Balance: ${MY_BALANCE}\n\n{txt}\nPage {page+1}/{total}"

def get_markup(page):
    total = math.ceil(len(MY_CARDS)/10)
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("Back", callback_data=f"page_{max(0,page-1)}"), types.InlineKeyboardButton("Next", callback_data=f"page_{min(total-1,page+1)}"))
    m.add(types.InlineKeyboardButton("Menu", callback_data="main_menu"))
    return m

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.username or message.from_user.first_name
    welcome = "Welcome @" + str(name) + " to X STOCK! Sell Buy deals in seconds."
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("X Checker Bot", url="https://t.me/XprepaidCheckerBot"))
    markup.add(types.InlineKeyboardButton("Support", url="https://t.me/twinlovetoma"))
    markup.add(types.InlineKeyboardButton("Listing", callback_data="listing_0"))
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    if "listing_" in call.data or "page_" in call.data:
        page = int(call.data.split("_")[1])
        bot.edit_message_text(get_text(page), call.message.chat.id, call.message.message_id, reply_markup=get_markup(page))
    elif call.data == "main_menu":
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "Coming soon!")

@app.route("/" + TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/")
def home():
    bot.remove_webhook()
    bot.set_webhook(url="https://" + os.environ.get('RENDER_EXTERNAL_HOSTNAME') + "/" + TOKEN)
    return "Bot Live", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
