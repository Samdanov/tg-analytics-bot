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

from app.services.workflow import run_full_analysis_pipeline

router = Router()

USERNAME_RE = re.compile(r"(?:t\.me/|@)([A-Za-z0-9_]{3,})")


def _extract_channel_from_message(message: Message):
    """
    Пытаемся достать username и title канала из:
    - пересланного поста из канала
    - текста с t.me/... или @username
    """
    username = None
    title = None

    # 1) Пересланный пост из канала
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        ch = message.forward_from_chat
        username = ch.username
        title = ch.title

    # 2) Текст с ссылкой/юзернеймом
    if not username and message.text:
        m = USERNAME_RE.search(message.text)
        if m:
            username = m.group(1)
            title = username  # если названия нет, покажем хотя бы @username

    if username:
        username = username.lstrip("@")

    return username, title


@router.message(F.text | F.forward_from_chat)
async def detect_channel_handler(message: Message):
    """
    Ловим произвольные сообщения и пытаемся найти в них канал.
    Если нашли — предлагаем кнопку 'Начать анализ'.
    """

    username, title = _extract_channel_from_message(message)
    if not username:
        # Ничего не нашли — молчим, чтобы не спамить
        return

    text = f"Найден канал:\n<b>{title or username}</b>\n@{username}\n\nНажми кнопку, чтобы запустить анализ."
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
    """
    Обрабатываем нажатие на кнопку 'Начать анализ'.
    Запускаем полный пайплайн и шлём XLSX или ошибку.
    """
    await callback.answer()  # убираем "часики" у кнопки

    data = callback.data.split(":", 1)
    if len(data) != 2:
        return await callback.message.answer("Некорректные данные для анализа.")

    username = data[1]

    msg = await callback.message.answer(f"Запускаю анализ для @{username}...\n"
                                        f"Это может занять немного времени.")

    try:
        report_path: Path = await run_full_analysis_pipeline(username)
    except ValueError as e:
        await msg.edit_text(f"⚠️ Не удалось выполнить анализ: {e}")
        return
    except Exception as e:
        await msg.edit_text(f"🔥 Ошибка: <code>{e}</code>")
        raise


    # Отправляем XLSX
    doc = FSInputFile(report_path)
    await msg.edit_text("✅ Анализ завершён, отправляю отчёт...")
    await callback.message.answer_document(
        document=doc,
        caption=f"📊 Отчёт по похожим каналам для @{username}",
    )
