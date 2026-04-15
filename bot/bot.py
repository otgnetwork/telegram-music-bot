import os
import sqlite3
import asyncio

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 1485749631
TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_"
DB_PATH = "referrals.db"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_mode = {}
admin_reply_target = {}
BOT_USERNAME = None

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        invited_by INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        inviter_id INTEGER,
        invited_user_id INTEGER UNIQUE
    )
    """)

    conn.commit()
    conn.close()


def register_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, invited_by) VALUES (?, NULL)", (user_id,))
    conn.commit()
    conn.close()


def save_ref(invited, inviter):
    if invited == inviter:
        return False

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT invited_by FROM users WHERE user_id=?", (invited,))
    row = cur.fetchone()

    if row and row[0]:
        conn.close()
        return False

    cur.execute("UPDATE users SET invited_by=? WHERE user_id=?", (inviter, invited))
    cur.execute("INSERT OR IGNORE INTO referrals VALUES (?,?)", (inviter, invited))

    conn.commit()
    conn.close()
    return True


def get_ref_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM referrals WHERE inviter_id=?", (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count


# ---------- UI ----------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎵 Найти музыку", callback_data="menu:music")
    kb.button(text="✨ Заказать песню", callback_data="menu:song")
    kb.button(text="📊 Мои приглашения", callback_data="menu:refs")
    kb.button(text="🎥 TikTok эфир", url=TIKTOK_URL)
    kb.adjust(1)
    return kb.as_markup()


def admin_reply_keyboard(user_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="✉️ Ответить клиенту", callback_data=f"reply:{user_id}")
    return kb.as_markup()


# ---------- START ----------
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_mode[user_id] = "music"

    register_user(user_id)

    # рефералка
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        inviter = int(args[1].replace("ref_", ""))
        save_ref(user_id, inviter)

    await message.answer(
        "🎧 <b>Хочешь персональную песню под заказ?</b>\n\n"
        "✨ Это не шаблон — это трек про вашу историю\n\n"
        "💝 Идеально для:\n"
        "— любимого человека ❤️\n"
        "— годовщины 💍\n"
        "— подарка 🎁\n\n"
        "🎶 Получится как настоящий трек — с эмоциями и смыслом\n\n"
        "👇 Выбери действие",
        reply_markup=main_menu()
    )


# ---------- CALLBACK ----------
@dp.callback_query(F.data == "menu:music")
async def music(cb: CallbackQuery):
    user_mode[cb.from_user.id] = "music"
    await cb.message.edit_text("🎵 Напиши название трека или исполнителя")
    await cb.answer()


@dp.callback_query(F.data == "menu:song")
async def song(cb: CallbackQuery):
    user_mode[cb.from_user.id] = "song"
    await cb.message.edit_text(
        "✨ <b>Я создам для тебя персональную песню</b>\n\n"
        "Напиши одним сообщением:\n"
        "— для кого песня\n"
        "— повод\n"
        "— стиль\n"
        "— настроение\n"
        "— важные детали"
    )
    await cb.answer()


@dp.callback_query(F.data == "menu:refs")
async def refs(cb: CallbackQuery):
    user_id = cb.from_user.id
    count = get_ref_count(user_id)

    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    await cb.message.answer(
        f"📊 <b>Твоя реферальная программа</b>\n\n"
        f"Приглашено: {count}\n\n"
        f"🔗 Твоя ссылка:\n{link}"
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("reply:"))
async def reply_to_user(cb: CallbackQuery):
    user_id = int(cb.data.split(":")[1])
    admin_reply_target[cb.from_user.id] = user_id

    await cb.message.answer(
        "✉️ Режим ответа включен\n\n"
        f"Следующее сообщение уйдет пользователю {user_id}\n"
        "Отмена: /cancel_reply"
    )
    await cb.answer()


# ---------- TEXT ----------
@dp.message()
async def text_handler(message: Message):
    user_id = message.from_user.id
    text = message.text
    mode = user_mode.get(user_id)

    # --- ответ админа ---
    if user_id in admin_reply_target:
        target = admin_reply_target[user_id]
        await bot.send_message(target, f"💬 Ответ менеджера:\n\n{text}")
        del admin_reply_target[user_id]
        await message.answer("✅ Ответ отправлен")
        return

    # --- заявка ---
    if mode == "song":
        await message.answer(
            "✅ <b>Заявка принята</b>\n\n"
            "Я скоро посмотрю и свяжусь с тобой 👌",
            reply_markup=main_menu()
        )

        await bot.send_message(
            ADMIN_ID,
            f"🔥 <b>НОВАЯ ЗАЯВКА</b>\n\n"
            f"ID: {user_id}\n\n{text}",
            reply_markup=admin_reply_keyboard(user_id)
        )
        return

    # --- поиск ---
    if mode == "music":
        await message.answer("🔎 Ищу... (пока заглушка)")
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
