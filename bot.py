import os, math
import telebot
from telebot import types
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
LTC_ADDRESS = "LNDgqKM2CQ3LZved7z3mnbwBFdBQUbySZt"
SOL_ADDRESS = "DVvg75XKBCsXcuo1Wxe7A3BYcW3sXA5zcd76NLMHFxGy"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ============ TUMI EKHANE EDIT KORBE ============
MY_BALANCE_USD = 8.22
MY_BALANCE_SOL = "0.0000000000"
MY_BALANCE_LTC = "0.1698255240"
TOTAL_CARDS = 101
TOTAL_BALANCE = "$1,392.79"

MY_CARDS = [
    "533985xx CAD$212.36 at 39%",
    "403446xx USD$118.43 at 39% 🅿️",
    "435880xx USD$100.00 at 39% 🅿️",
    "435880xx USD$99.16 at 39% 🔄",
    "435880xx USD$80.26 at 39%",
    "461126xx CAD$78.58 at 39% 🅿️",
    "533937xx CAD$75.00 at 39%",
    "533985xx CAD$67.09 at 39%",
    "525362xx USD$63.32 at 39%",
    "403446xx USD$54.42 at 39% 🔄",
]
# ============ EDIT SES ============

CARDS_PER_PAGE = 10

def get_listing_text(page):
    total_pages = math.ceil(len(MY_CARDS)/10)
    start = page * 10
    page_cards = MY_CARDS[start:start+10]
    cards_text = ""
    for i, card in enumerate(page_cards, start=start+1):
        cards_text += f"{i}. {card}\n"
    return f"""Your Balance:
💵 USD: ${MY_BALANCE_USD}
- SOL: {MY_BALANCE_SOL} ($0.00)
- LTC: {MY_BALANCE_LTC} (${MY_BALANCE_USD})

{cards_text}
Total Cards: {TOTAL_CARDS} | Total Cards Balance: {TOTAL_BALANCE}

Legend:
🔄 = Re-listed
G = Used on Google
🅿️ = Used on PayPal

Page {page+1}/{total_pages}"""

def get_listing_markup(page):
    total_pages = math.ceil(len(MY_CARDS)/10) if MY_CARDS else 1
    markup = types.InlineKeyboardMarkup(row_width=4)
    markup.add(
        types.InlineKeyboardButton("⏪ First", callback_data=f"page_0"),
        types.InlineKeyboardButton("⬅️ Back", callback_data=f"page_{max(0, page-1)}"),
        types.InlineKeyboardButton("Next ➡️", callback_data=f"page_{min(total_pages-1, page+1)}"),
        types.InlineKeyboardButton("⏩ Last", callback_data=f"page_{total_pages-1}")
    )
    markup.add(
        types.InlineKeyboardButton("⏪ -5", callback_data=f"page_{max(0, page-5)}"),
        types.InlineKeyboardButton("⏩ +5", callback_data=f"page_{min(total_pages-1, page+5)}")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
    text = f"⚡ Welcome {user} to X STOCK! ⚡\n
