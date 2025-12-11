from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.usecases.channel_service import add_channel_usecase

router = Router()


@router.message(Command("add_channel"))
async def add_channel_handler(message: Message):
    """
    /add_channel @username
    Парсит канал, сохраняет в БД, пишет результат.
    """
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: <code>/add_channel @username</code>")

    raw = args[1]

    channel_data, channel_id, posts_count, error = await add_channel_usecase(raw_username=raw, post_limit=50)

    if error:
        return await message.answer(f"❌ {error}")

    await message.answer(
        f"✅ Канал сохранён в БД\n"
        f"<b>{channel_data['title']}</b>\n"
        f"username: @{channel_data['username']}\n"
        f"ID в БД: {channel_id}\n"
        f"Сохранено постов: {posts_count}"
    )
