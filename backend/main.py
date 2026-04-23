from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
import html
from datetime import datetime
import uuid

app = FastAPI()

origins = [
    "https://otg-mini-app-clean-production.up.railway.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = os.getenv("MANAGER_CHAT_ID")


class SongOrder(BaseModel):
    client_name: str
    telegram_username: str = ""
    phone: str = ""
    preferred_contact: str = ""
    song_type: str = ""
    occasion: str = ""
    mood_style: str = ""
    references: str = ""
    language: str = ""
    deadline: str = ""
    budget: str = ""
    details: str


@app.get("/search")
def search(q: str):
    url = f"https://api.deezer.com/search?q={q}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    result = []
    for item in data.get("data", []):
        result.append({
            "title": item.get("title"),
            "artist": item.get("artist", {}).get("name"),
            "preview_url": item.get("preview"),
        })

    return result


def send_manager_message(text: str) -> None:
    if not BOT_TOKEN or not MANAGER_CHAT_ID:
        raise HTTPException(
            status_code=500,
            detail="BOT_TOKEN or MANAGER_CHAT_ID is not configured in backend service"
        )

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(
        telegram_url,
        json={
            "chat_id": MANAGER_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    resp.raise_for_status()


@app.post("/song-order")
def create_song_order(order: SongOrder):
    order_id = f"OTG-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    msg = (
        f"🎼 <b>Новый заказ песни</b>\n"
        f"🆔 <b>ID:</b> {html.escape(order_id)}\n"
        f"🕒 <b>Дата:</b> {html.escape(datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))}\n\n"
        f"👤 <b>Имя:</b> {html.escape(order.client_name)}\n"
        f"📨 <b>Telegram:</b> {html.escape(order.telegram_username or '—')}\n"
        f"📞 <b>Телефон:</b> {html.escape(order.phone or '—')}\n"
        f"☎️ <b>Предпочтительный контакт:</b> {html.escape(order.preferred_contact or '—')}\n\n"
        f"🎵 <b>Тип песни:</b> {html.escape(order.song_type or '—')}\n"
        f"🎉 <b>Повод:</b> {html.escape(order.occasion or '—')}\n"
        f"🎭 <b>Настроение / стиль:</b> {html.escape(order.mood_style or '—')}\n"
        f"🌍 <b>Язык:</b> {html.escape(order.language or '—')}\n"
        f"⏳ <b>Дедлайн:</b> {html.escape(order.deadline or '—')}\n"
        f"💶 <b>Бюджет:</b> {html.escape(order.budget or '—')}\n"
        f"🎧 <b>Референсы:</b> {html.escape(order.references or '—')}\n\n"
        f"📝 <b>Подробное ТЗ:</b>\n{html.escape(order.details)}"
    )

    send_manager_message(msg)

    return {
        "ok": True,
        "order_id": order_id,
        "message": "Заявка отправлена менеджеру"
    }
