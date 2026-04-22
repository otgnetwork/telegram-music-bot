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
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    WebAppInfo,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
ADMIN_ID = 1485749631
TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_"
MINI_APP_URL = "https://otg-mini-app-clean-production.up.railway.app"
DB_PATH = "referrals.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

user_mode: dict[int, str] = {}
admin_reply_target: dict[int, int] = {}
BOT_USERNAME: str | None = None


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            invited_by INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            inviter_id INTEGER NOT NULL,
            invited_user_id INTEGER NOT NULL UNIQUE
        )
    """)

    conn.commit()
    conn.close()


def register_user_if_needed(user_id: int) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, invited_by) VALUES (?, NULL)",
        (user_id,)
    )
    conn.commit()
    conn.close()


def save_referral(invited_user_id: int, inviter_id: int) -> bool:
    if invited_user_id == inviter_id:
        return False

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, invited_by) VALUES (?, NULL)",
        (invited_user_id,)
    )
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, invited_by) VALUES (?, NULL)",
        (inviter_id,)
    )

    cur.execute("SELECT invited_by FROM users WHERE user_id = ?", (invited_user_id,))
    row = cur.fetchone()

    if row and row["invited_by"] is not None:
        conn.close()
        return False

    cur.execute(
        "UPDATE users SET invited_by = ? WHERE user_id = ? AND invited_by IS NULL",
        (inviter_id, invited_user_id),
    )

    if cur.rowcount == 0:
        conn.close()
        return False

    cur.execute(
        "INSERT OR IGNORE INTO referrals (inviter_id, invited_user_id) VALUES (?, ?)",
        (inviter_id, invited_user_id),
    )

    conn.commit()
    conn.close()
    return True


def get_referrals_count(inviter_id: int) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS total FROM referrals WHERE inviter_id = ?",
        (inviter_id,)
    )
    row = cur.fetchone()
    conn.close()
    return int(row["total"]) if row else 0


def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Открыть OTG Media",
        web_app=WebAppInfo(url=MINI_APP_URL)
    )
    builder.button(text="🎥 Музыкальный эфир OTG в TikTok", url=TIKTOK_URL)
    builder.adjust(1)
    return builder.as_markup()


def after_request_menu():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🚀 Открыть OTG Media",
        web_app=WebAppInfo(url=MINI_APP_URL)
    )
    builder.button(text="📊 Мои приглашения", callback_data="menu:myrefs")
    builder.button(text="🎥 Музыкальный эфир OTG в TikTok", url=TIKTOK_URL)
    builder.adjust(1)
    return builder.as_markup()


def admin_reply_keyboard(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✉️ Ответить клиенту",
        callback_data=f"admin_reply:{user_id}"
    )
    return builder.as_markup()


def share_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Мои приглашения", callback_data="menu:myrefs")
    builder.adjust(1)
    return builder.as_markup()


def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/*?:"<>|]', "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:80] or "track"


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject | None = None):
    user_mode[message.from_user.id] = "music"
    register_user_if_needed(message.from_user.id)

    referral_saved = False
    inviter_id = None

    if command and command.args and command.args.startswith("ref_"):
        raw_id = command.args.replace("ref_", "", 1)
        if raw_id.isdigit():
            inviter_id = int(raw_id)
            referral_saved = save_referral(
                invited_user_id=message.from_user.id,
                inviter_id=inviter_id,
            )

    text = (
        "🚀 <b>OTG Media Network</b>\n\n"
        "Музыка, клипы и персональные песни — в одном месте.\n\n"
        "👇 Открой приложение"
    )

    if referral_saved:
        text += "\n\n🎁 <b>Ты пришёл по приглашению друга</b>"

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu()
    )

    if referral_saved and inviter_id:
        try:
            await bot.send_message(
                inviter_id,
                "🎉 <b>У тебя новый приглашённый пользователь!</b>\n\n"
                f"Всего приглашений: <b>{get_referrals_count(inviter_id)}</b>"
            )
        except Exception:
            pass


@dp.message(F.text == "/myrefs")
async def my_refs(message: Message) -> None:
    register_user_if_needed(message.from_user.id)

    if BOT_USERNAME:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{message.from_user.id}"
    else:
        ref_link = "Бот ещё инициализируется, попробуй чуть позже."

    total = get_referrals_count(message.from_user.id)

    await message.answer(
        "📊 <b>Твоя реферальная программа</b>\n\n"
        f"<b>Приглашено:</b> {total}\n\n"
        f"<b>Твоя ссылка:</b>\n<code>{ref_link}</code>\n\n"
        "Отправь её друзьям 👇"
    )

    await message.answer(
        "Управление рефералкой:",
        reply_markup=share_keyboard()
    )


@dp.callback_query(F.data == "menu:myrefs")
async def menu_myrefs(callback: CallbackQuery) -> None:
    register_user_if_needed(callback.from_user.id)

    if BOT_USERNAME:
        ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    else:
        ref_link = "Бот ещё инициализируется, попробуй чуть позже."

    total = get_referrals_count(callback.from_user.id)

    await callback.message.answer(
        "📊 <b>Твоя реферальная программа</b>\n\n"
        f"<b>Приглашено:</b> {total}\n\n"
        f"<b>Твоя ссылка:</b>\n<code>{ref_link}</code>\n\n"
        "Отправь её друзьям 👇"
    )

    await callback.message.answer(
        "Управление рефералкой:",
        reply_markup=share_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:song")
async def menu_song(callback: CallbackQuery) -> None:
    user_mode[callback.from_user.id] = "song"

    await callback.message.edit_text(
        "✨ <b>Я создам для тебя персональную песню</b>\n\n"
        "Это будет не шаблон — а трек именно про вашу историю ❤️\n\n"
        "🔥 Напиши одним сообщением:\n"
        "— для кого песня\n"
        "— повод\n"
        "— стиль\n"
        "— настроение\n"
        "— важные детали\n\n"
        "💡 Чем подробнее — тем сильнее получится результат",
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("admin_reply:"))
async def admin_reply_start(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    user_id = int(callback.data.split(":", 1)[1])
    admin_reply_target[callback.from_user.id] = user_id

    await callback.answer("Режим ответа включен")
    await callback.message.answer(
        "✉️ <b>Режим ответа клиенту включен</b>\n\n"
        f"Следующее сообщение уйдет пользователю <code>{user_id}</code>\n\n"
        "Отмена: /cancel_reply"
    )


async def fetch_tracks(query: str) -> list[dict]:
    url = f"{BACKEND_URL}/search"
    params = {"q": query}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=20) as response:
            response.raise_for_status()
            data = await response.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("results", [])
    return []


async def download_preview(preview_url: str) -> bytes:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(preview_url, timeout=30) as response:
            response.raise_for_status()
            return await response.read()


@dp.message(F.text == "/cancel_reply")
async def cancel_reply(message: Message) -> None:
    if message.from_user.id in admin_reply_target:
        del admin_reply_target[message.from_user.id]
        await message.answer("Режим ответа отключен.")


@dp.message()
async def handle_text(message: Message) -> None:
    text = (message.text or "").strip()

    if not text:
        await message.answer("Отправь текстовый запрос.")
        return

    register_user_if_needed(message.from_user.id)

    if message.from_user.id == ADMIN_ID and message.from_user.id in admin_reply_target:
        target_user_id = admin_reply_target[message.from_user.id]

        await bot.send_message(
            target_user_id,
            "📩 <b>Ответ от менеджера:</b>\n\n" + text
        )

        await message.answer("✅ Сообщение отправлено клиенту.")
        del admin_reply_target[message.from_user.id]
        return

    mode = user_mode.get(message.from_user.id, "music")

    if mode == "song":
        username = f"@{message.from_user.username}" if message.from_user.username else "без username"
        full_name = message.from_user.full_name or "Без имени"

        await message.answer(
            "🎤 <b>Твоя заявка принята!</b>\n\n"
            "Вот что мы получили:\n"
            f"<blockquote>{text}</blockquote>\n\n"
            "Я скоро посмотрю заявку и свяжусь с тобой 👌",
            parse_mode="HTML"
        )

        await message.answer(
            "Можешь выбрать следующее действие:",
            reply_markup=after_request_menu()
        )

        await bot.send_message(
            ADMIN_ID,
            "<b>🔥 НОВАЯ ЗАЯВКА НА ПЕСНЮ</b>\n\n"
            f"<b>Имя:</b> {full_name}\n"
            f"<b>Username:</b> {username}\n"
            f"<b>User ID:</b> <code>{message.from_user.id}</code>\n\n"
            f"<b>Текст заявки:</b>\n<blockquote>{text}</blockquote>",
            reply_markup=admin_reply_keyboard(message.from_user.id)
        )
        return

    await message.answer(
        "🚀 Основной функционал теперь внутри <b>OTG Media</b>.\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение:",
        reply_markup=main_menu()
    )


async def main():
    global BOT_USERNAME

    init_db()

    me = await bot.get_me()
    BOT_USERNAME = me.username

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
