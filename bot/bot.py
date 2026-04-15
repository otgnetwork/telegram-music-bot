import os
import re
import ssl
import asyncio
import aiohttp
import certifi

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
ADMIN_ID = 1485749631
TIKTOK_URL = "https://www.tiktok.com/@alexey_pv_"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in .env")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

user_mode: dict[int, str] = {}
admin_reply_target: dict[int, int] = {}


def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎵 Найти музыку", callback_data="menu:music")
    builder.button(text="✨ Заказать песню", callback_data="menu:song")
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


def safe_filename(value: str) -> str:
    value = re.sub(r'[\\/*?:"<>|]', "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:80] or "track"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_mode[message.from_user.id] = "music"

    await message.answer(
        "🎧 <b>Привет! Я делаю персональные песни под заказ</b>\n\n"
        "🔥 Подойдет для:\n"
        "— любимой ❤️\n"
        "— годовщины 💍\n"
        "— подарка 🎁\n\n"
        "🎬 Я также веду живые эфиры в TikTok — можешь залететь прямо сейчас 👇",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "menu:music")
async def menu_music(callback: CallbackQuery) -> None:
    user_mode[callback.from_user.id] = "music"

    await callback.message.edit_text(
        "<b>🎵 Поиск музыки</b>\n\n"
        "Отправь название трека или исполнителя.\n"
        "Пример: <code>Eminem</code>",
        reply_markup=main_menu()
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

    return data.get("results", [])


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

    # Ответ клиенту от админа
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

    # Заявка на песню
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
            reply_markup=main_menu()
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

    # Поиск музыки
    await message.answer("🔎 Ищу...")

    results = await fetch_tracks(text)

    if not results:
        await message.answer("Ничего не найдено.", reply_markup=main_menu())
        return

    for item in results[:3]:
        artist = item["artist"]["name"]
        title = item["title"]
        preview = item["preview"]

        audio_bytes = await download_preview(preview)

        await message.answer_audio(
            audio=BufferedInputFile(
                audio_bytes,
                filename=f"{safe_filename(title)} - {safe_filename(artist)}.mp3"
            ),
            caption=f"{artist} — {title}",
            title=title,
            performer=artist
        )

    await message.answer(
        "Можешь выбрать следующее действие:",
        reply_markup=main_menu()
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
