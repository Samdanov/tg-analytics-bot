# app/bot/handlers/workflow.py

import re
import time
from pathlib import Path

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
)

from app.services.usecases.channel_service import run_full_pipeline_usecase
from app.services.helpers import build_channel_summary

router = Router()

USERNAME_RE = re.compile(r"(?:t\.me/|@)([A-Za-z0-9_]{3,})")

# Простой кеш для дедупликации media_group
_media_group_cache = {}
_CACHE_TTL = 60  # секунд


def _is_duplicate_media_group(media_group_id: str | None) -> bool:
    """Проверяет, был ли уже обработан этот media_group."""
    if not media_group_id:
        return False
    
    now = time.time()
    # Очистка устаревших записей
    expired = [k for k, v in _media_group_cache.items() if now - v > _CACHE_TTL]
    for k in expired:
        _media_group_cache.pop(k, None)
    
    if media_group_id in _media_group_cache:
        return True
    
    _media_group_cache[media_group_id] = now
    return False


def _extract_channel_from_message(message: Message):
    """
    Пытаемся достать username и title канала из:
    - пересланного поста
    - текста с ссылкой t.me/... или @username
    """
    username = None
    title = None

    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        ch = message.forward_from_chat
        username = ch.username
        title = ch.title

    if not username and message.text:
        m = USERNAME_RE.search(message.text)
        if m:
            username = m.group(1)
            title = username
    
    # Также проверяем caption (для постов с картинками)
    if not username and message.caption:
        m = USERNAME_RE.search(message.caption)
        if m:
            username = m.group(1)
            title = username

    if username:
        username = username.lstrip("@")

    return username, title


@router.message(F.text | F.forward_from_chat | F.photo | F.video)
async def detect_channel_handler(message: Message):
    # Игнорируем дубликаты из media_group (альбомы)
    if _is_duplicate_media_group(message.media_group_id):
        return

    username, title = _extract_channel_from_message(message)
    if not username:
        return

    username = username.strip()

    text = (
        f"Найден канал:\n"
        f"<b>{title or username}</b>\n"
        f"@{username}\n\n"
        f"Выбери количество похожих каналов для анализа:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔟 10 каналов", callback_data=f"analyze:{username}:10"),
                InlineKeyboardButton(text="2️⃣5️⃣ 25 каналов", callback_data=f"analyze:{username}:25"),
            ],
            [
                InlineKeyboardButton(text="5️⃣0️⃣ 50 каналов", callback_data=f"analyze:{username}:50"),
                InlineKeyboardButton(text="💯 100 каналов", callback_data=f"analyze:{username}:100"),
            ],
            [
                InlineKeyboardButton(text="🔢 500 каналов (макс)", callback_data=f"analyze:{username}:500"),
            ],
        ]
    )

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("analyze:"))
async def start_analysis_callback(callback: CallbackQuery):
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.message.answer("❌ Ошибка: неверный формат команды")
        return
    
    username = parts[1]
    top_n = int(parts[2])

    msg = await callback.message.answer(
        f"Запускаю анализ для @{username}...\n"
        f"Поиск {top_n} похожих каналов. Это может занять немного времени..."
    )

    try:
        report_path: Path = await run_full_pipeline_usecase(username, top_n=top_n)
    except ValueError as e:
        await msg.edit_text(f"⚠️ Не удалось выполнить анализ: {e}")
        return
    except Exception as e:
        await msg.edit_text(f"🔥 Ошибка: <code>{e}</code>")
        raise

    summary = await build_channel_summary(username)
    await callback.message.answer(summary)

    doc = FSInputFile(report_path)
    await msg.edit_text("✅ Анализ завершён, отправляю отчёт...")

    await callback.message.answer_document(
        document=doc,
        caption=f"📊 Отчёт: {top_n} похожих каналов для @{username}",
    )
