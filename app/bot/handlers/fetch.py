from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telethon import functions
from telethon.errors import (
    UsernameNotOccupiedError,
    UsernameInvalidError,
)

from app.services.telegram_parser.client import client

router = Router()


async def resolve_channel(username: str):
    """
    Строгое разрешение username → канал.
    Работает только с настоящими каналами.
    """

    # Нормализуем ввод
    username = (
        username.strip()
        .replace("https://t.me/", "")
        .replace("http://t.me/", "")
        .replace("t.me/", "")
        .replace("@", "")
    )

    if not username:
        return None, "Некорректный username"

    try:
        result = await client(functions.contacts.ResolveUsernameRequest(username))

        if not result.chats:
            return None, "Канал не найден"

        entity = result.chats[0]

        # Проверка: это канал?
        if not getattr(entity, "broadcast", False):
            return None, "Это не канал (чат/группа/пользователь)"

        return entity, None

    except UsernameNotOccupiedError:
        return None, "Такого username не существует"

    except UsernameInvalidError:
        return None, "Некорректный username"

    except Exception as e:
        return None, f"Ошибка Telegram API: {type(e).__name__}: {e}"


@router.message(Command("fetch"))
async def fetch_handler(message: Message):
    """
    Команда: /fetch @username
    """

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /fetch @username")

    username = args[1]

    entity, error = await resolve_channel(username)

    if error:
        return await message.answer(f"❌ {error}")

    text = (
        "✅ <b>Канал найден</b>\n"
        f"<b>Название:</b> {entity.title}\n"
        f"<b>Username:</b> @{entity.username}\n"
        f"<b>ID:</b> {entity.id}"
    )

    await message.answer(text)
