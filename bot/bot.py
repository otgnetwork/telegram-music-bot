import os
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    MenuButtonDefault,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = "https://otg-mini-app-clean-production.up.railway.app"
TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_/"

START_TEXT = (
    "🚀 <b>OTG Media Network</b>\n\n"
    "Музыка, клипы и персональные песни — в одном месте.\n\n"
    "👇 Нажми кнопку ниже, чтобы открыть приложение"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("🚀 Открыть OTG Media", web_app=WebAppInfo(url=MINI_APP_URL))]],
        resize_keyboard=True,
        is_persistent=True,
    )

    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Музыкальный эфир OTG в TikTok", url=TIKTOK_URL)]
    ])

    await update.message.reply_html(START_TEXT, reply_markup=reply_keyboard)
    await update.message.reply_text("Дополнительно:", reply_markup=inline_keyboard)

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
