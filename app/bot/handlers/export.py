# app/bot/handlers/export.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from app.services.xlsx_generator import generate_similar_channels_xlsx

router = Router()


@router.message(Command("export"))
async def export_handler(message: Message):
    """
    /export @username
    Генерирует XLSX с похожими каналами и отправляет файл.
    """
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: <code>/export @username</code>")

    raw_username = args[1].strip()

    await message.answer("Генерирую XLSX-отчёт, подожди пару секунд...")

    try:
        path = await generate_similar_channels_xlsx(raw_username)
    except ValueError as e:
        return await message.answer(f"⚠️ {e}")
    except Exception as e:
        # Логировать имеет смысл, но тут просто честно
        return await message.answer("Произошла внутренняя ошибка при генерации отчёта.")

    doc = FSInputFile(path)
    await message.answer_document(
        document=doc,
        caption=f"📊 Отчёт по похожим каналам для {raw_username}",
    )
