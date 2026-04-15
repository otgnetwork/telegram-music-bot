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
from aiogram.types import Message, CallbackQuery, BufferedInputFile
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
admin_reply_target = {}
BOT_USERNAME = None

# ---------- AI генерация ----------
async def generate_song_text(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты профессиональный автор песен. Пиши красиво, с куплетами и припевом."},
            {"role": "user", "content": f"Создай песню на основе:\n{prompt}"}
        ],
        temperature=0.9
    )
    return response.choices[0].message.content


# ---------- БД ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, invited_by INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS referrals (inviter_id INTEGER, invited_user_id INTEGER UNIQUE)")
    conn.commit()
    conn.close()

def register_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, invited_by) VALUES (?, NULL)", (user_id,))
    conn.commit()
    conn.close()

def save_ref(invited, inviter):
    if invited == inviter:
        return False

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT invited_by FROM users WHERE user_id=?", (invited,))
    row = cur.fetchone()

    if row and row["invited_by"]:
        conn.close()
        return False

    cur.execute("UPDATE users SET invited_by=? WHERE user_id=?", (inviter, invited))
    cur.execute("INSERT OR IGNORE INTO referrals VALUES (?,?)", (inviter, invited))

    conn.commit()
    conn.close()
    return True

def get_ref_count(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM referrals WHERE inviter_id=?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res["c"] if res else 0


# ---------- UI ----------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎵 Найти музыку", callback_data="menu:music")
    kb.button(text="✨ Заказать песню", callback_data="menu:song")
    kb.button(text="🤖 Сгенерировать песню", callback_data="menu:ai_song")
    kb.button(text="🎥 TikTok эфир", url=TIKTOK_URL)
    kb.adjust(1)
    return kb.as_markup()

def share_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Мои приглашения", callback_data="menu:refs")
    kb.adjust(1)
    return kb.as_markup()


# ---------- START ----------
@dp.message(CommandStart())
async def start(message: Message, command: CommandObject = None):
    user_mode[message.from_user.id] = "music"
    register_user(message.from_user.id)

    if command and command.args and command.args.startswith("ref_"):
        inviter = int(command.args.split("_")[1])
        save_ref(message.from_user.id, inviter)

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
    await cb.message.answer("🤖 Опиши песню (для кого, стиль и т.д.)")
    await cb.answer()

@dp.callback_query(F.data == "menu:refs")
async def refs(cb: CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{cb.from_user.id}"
    count = get_ref_count(cb.from_user.id)

    await cb.message.answer(
        f"📊 Приглашено: {count}\n\n"
        f"🔗 {link}"
    )
    await cb.answer()


# ---------- TEXT ----------
@dp.message()
async def text_handler(message: Message):
    mode = user_mode.get(message.from_user.id)

    if mode == "ai_song":
        await message.answer("🎧 Генерирую...")

        song = await generate_song_text(message.text)

        await message.answer(f"✨\n\n{song}", reply_markup=main_menu())
        return

    if mode == "song":
        await message.answer("✅ Заявка принята", reply_markup=main_menu())
        return

    if mode == "music":
        await message.answer("🔎 Ищу... (заглушка)")
        return


# ---------- RUN ----------
async def main():
    global BOT_USERNAME
    init_db()
    me = await bot.get_me()
    BOT_USERNAME = me.username
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
