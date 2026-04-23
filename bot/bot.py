import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonDefault
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = "https://otg-mini-app-clean-production.up.railway.app"
TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_/"

START_TEXT = (
    "🚀 <b>OTG Media Network TEST</b>\n\n"
    f"<b>URL:</b> {MINI_APP_URL}\n\n"
    "Нажми кнопку ниже."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 TEST OPEN APP", url=MINI_APP_URL)],
        [InlineKeyboardButton("🎬 TikTok", url=TIKTOK_URL)],
    ])
    await update.message.reply_html(START_TEXT, reply_markup=keyboard)

async def reset_menu_button(application: Application) -> None:
    await application.bot.set_chat_menu_button(menu_button=MenuButtonDefault())

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(reset_menu_button)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
