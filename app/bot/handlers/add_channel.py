from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.telegram_parser.channel_info import get_channel_with_posts
from db.repo import get_pool, save_channel, save_posts

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

    channel_data, posts, error = await get_channel_with_posts(raw_username=raw, limit=50)

    if error:
        return await message.answer(f"❌ {error}")

    pool = await get_pool()
    channel_id = await save_channel(pool, channel_data)
    await save_posts(pool, channel_id, posts)

    await message.answer(
        f"✅ Канал сохранён в БД\n"
        f"<b>{channel_data['title']}</b>\n"
        f"username: @{channel_data['username']}\n"
        f"ID в БД: {channel_id}\n"
        f"Сохранено постов: {len(posts)}"
    )
