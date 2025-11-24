from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from services.telegram_parser.client import client

router = Router()

@router.message(Command("fetch"))
async def fetch_handler(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /fetch @username")

    username = args[1]

    try:
        entity = await client.get_entity(username)
        await message.answer(f"Канал найден:\n<b>{entity.title}</b>\n@{entity.username}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")