import os
import re
import ssl
import sqlite3
import asyncio
import aiohttp
import certifi

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- AI ---
from openai import OpenAI

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

ADMIN_ID = 1485749631
TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_"
DB_PATH = "referrals.db"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_mode = {}
BOT_USERNAME = None


# ---------- 🔥 FIXED AI ----------
async def generate_song_text(prompt: str) -> str:
    loop = asyncio.get_event_loop()

    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты профессиональный автор песен. Пиши красиво, с куплетами и припевом."
                },
                {
                    "role": "user",
                    "content": f"Создай песню на основе:\n{prompt}"
                }
            ],
            temperature=0.9
        )
    )

    return response.choices[0].message.content


# ---------- UI ----------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎵 Найти музыку", callback_data="menu:music")
    kb.button(text="✨ Заказать песню", callback_data="menu:song")
    kb.button(text="🤖 Сгенерировать песню", callback_data="menu:ai_song")
    kb.button(text="🎥 TikTok эфир", url=TIKTOK_URL)
    kb.adjust(1)
    return kb.as_markup()


# ---------- START ----------
@dp.message(CommandStart())
async def start(message: Message, command: CommandObject = None):
    user_mode[message.from_user.id] = "music"

    await message.answer(
        "🎧 <b>Я делаю персональные песни</b>\n\n"
        "✨ Для подарков, отношений и эмоций\n\n"
        "👇 Выбери действие",
        reply_markup=main_menu()
    )


# ---------- CALLBACK ----------
@dp.callback_query(F.data == "menu:music")
async def music(cb: CallbackQuery):
    user_mode[cb.from_user.id] = "music"
    await cb.message.edit_text("🎵 Напиши название трека")
    await cb.answer()


@dp.callback_query(F.data == "menu:song")
async def song(cb: CallbackQuery):
    user_mode[cb.from_user.id] = "song"
    await cb.message.edit_text("✨ Напиши детали для песни")
    await cb.answer()


@dp.callback_query(F.data == "menu:ai_song")
async def ai_song(cb: CallbackQuery):
    user_mode[cb.from_user.id] = "ai_song"

    await cb.message.answer(
        "🤖 Напиши одним сообщением:\n\n"
        "— для кого песня\n"
        "— повод\n"
        "— стиль\n"
        "— настроение\n\n"
        "Я сгенерирую песню 🎧"
    )

    await cb.answer()


# ---------- TEXT ----------
@dp.message()
async def text_handler(message: Message):
    user_id = message.from_user.id
    mode = user_mode.get(user_id)

    # --- AI режим ---
    if mode == "ai_song":
        await message.answer("🎧 Генерирую песню...")

        try:
            song = await generate_song_text(message.text)

            await message.answer(
                f"✨ Вот твоя песня:\n\n{song}",
                reply_markup=main_menu()
            )

        except Exception as e:
            await message.answer("❌ Ошибка генерации. Попробуй позже.")
            print("AI ERROR:", e)

        user_mode[user_id] = "music"
        return

    # --- Заявка ---
    if mode == "song":
        await message.answer("✅ Заявка принята", reply_markup=main_menu())
        return

    # --- Поиск ---
    if mode == "music":
        await message.answer("🔎 Ищу... (заглушка)")
        return


# ---------- RUN ----------
async def main():
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
