# app/bot/handlers/workflow.py

import re
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

    if username:
        username = username.lstrip("@")

    return username, title


@router.message(F.text | F.forward_from_chat)
async def detect_channel_handler(message: Message):
    username, title = _extract_channel_from_message(message)
    if not username:
        return

    username = username.strip()

    text = (
        f"Найден канал:\n"
        f"<b>{title or username}</b>\n"
        f"@{username}\n\n"
        f"Нажми кнопку, чтобы запустить анализ."
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Начать анализ",
                    callback_data=f"start_analysis:{username}",
                )
            ]
        ]
    )

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("start_analysis:"))
async def start_analysis_callback(callback: CallbackQuery):
    await callback.answer()

    username = callback.data.split(":", 1)[1]

    msg = await callback.message.answer(
        f"Запускаю анализ для @{username}...\nЭто может занять немного времени..."
    )

    try:
        report_path: Path = await run_full_pipeline_usecase(username)
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
        caption=f"📊 Отчёт по похожим каналам для @{username}",
    )
