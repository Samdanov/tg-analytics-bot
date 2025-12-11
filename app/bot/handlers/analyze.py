from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.usecases.channel_service import analyze_usecase

router = Router()


@router.message(Command("analyze"))
async def analyze_handler(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /analyze @username")

    username = args[1]

    result, error = await analyze_usecase(username, post_limit=50)
    if error:
        return await message.answer(f"❌ {error}")

    await message.answer(
        f"📊 Анализ готов!\n\n"
        f"<b>Аудитория:</b> {result.get('audience')}\n\n"
        f"<b>Ключевые слова:</b>\n" +
        ", ".join(result.get("keywords", []))
    )
