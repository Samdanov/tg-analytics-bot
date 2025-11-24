from typing import Tuple, Optional, Dict, Any, List

from telethon import functions
from telethon.errors import UsernameNotOccupiedError, UsernameInvalidError

from .client import client


def _normalize_username(raw: str) -> str:
    return (
        raw.strip()
        .replace("https://t.me/", "")
        .replace("http://t.me/", "")
        .replace("t.me/", "")
        .replace("@", "")
    )


async def get_channel_with_posts(
    raw_username: str,
    limit: int = 50,
) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Возвращает (инфо_о_канале, список_постов, ошибка)
    """

    username = _normalize_username(raw_username)
    if not username:
        return None, None, "Некорректный username"

    try:
        result = await client(functions.contacts.ResolveUsernameRequest(username))

        if not result.chats:
            return None, None, "Канал не найден"

        entity = result.chats[0]

        if not getattr(entity, "broadcast", False):
            return None, None, "Это не канал (чат/группа/пользователь)"

        # подробная инфа о канале
        full = await client(functions.channels.GetFullChannelRequest(entity))

        channel_data = {
            "id": entity.id,
            "title": entity.title,
            "username": entity.username,
            "about": getattr(full.full_chat, "about", "") or "",
            "participants_count": getattr(full.full_chat, "participants_count", 0) or 0,
        }

        # последние посты
        messages = await client.get_messages(entity, limit=limit)
        posts: List[Dict[str, Any]] = []

        for m in messages:
            if not m.message:
                continue
            posts.append(
                {
                    "date": m.date,
                    "views": m.views or 0,
                    "forwards": m.forwards or 0,
                    "text": m.message,
                }
            )

        return channel_data, posts, None

    except UsernameNotOccupiedError:
        return None, None, "Такого username не существует"
    except UsernameInvalidError:
        return None, None, "Некорректный username"
    except Exception as e:
        return None, None, f"Ошибка Telegram API: {type(e).__name__}: {e}"
