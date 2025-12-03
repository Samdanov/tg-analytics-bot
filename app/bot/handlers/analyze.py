from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.repo import get_pool
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.services.llm.analyzer import analyze_channel, save_analysis

router = Router()


@router.message(Command("analyze"))
async def analyze_handler(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /analyze @username")

    username = args[1]

    pool = await get_pool()

    # Из БД берём канал и его посты
    channel, posts, error = await get_channel_with_posts(username, limit=50)
    if error:
        return await message.answer(f"❌ {error}")

    # Ищем ID в таблице channels
    row = await pool.fetchrow(
        "SELECT id FROM channels WHERE username = $1",
        channel["username"]
    )

    if not row:
        return await message.answer("Сначала добавьте канал командой /add_channel")

    channel_id = row["id"]

    # Аналитика
    result = await analyze_channel(channel, posts)

    # Сохраняем
    await save_analysis(channel_id, result)

    await message.answer(
        f"📊 Анализ готов!\n\n"
        f"<b>Аудитория:</b> {result.get('audience')}\n\n"
        f"<b>Ключевые слова:</b>\n" +
        ", ".join(result.get("keywords", []))
    )
