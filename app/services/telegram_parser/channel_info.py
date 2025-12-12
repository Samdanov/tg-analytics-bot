from typing import Tuple, Optional, Dict, Any, List
import asyncio

from telethon.errors import (
    UsernameInvalidError,
    UsernameNotOccupiedError,
    ChannelInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    RPCError,
)
from telethon.tl.functions.channels import GetFullChannelRequest

from .client import client, start_client


def _normalize_username(raw: str) -> str:
    return (
        raw.strip()
        .replace("https://t.me/", "")
        .replace("http://t.me/", "")
        .replace("t.me/", "")
        .replace("@", "")
    )


async def _with_retries(coro_factory, attempts: int = 3, base_delay: float = 1.0, timeout: float = 20.0):
    last_exc = None
    for attempt in range(attempts):
        try:
            return await asyncio.wait_for(coro_factory(), timeout=timeout)
        except Exception as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(base_delay * (2 ** attempt))
    if last_exc:
        raise last_exc


async def get_channel_with_posts(
    raw_username: str,
    limit: int = 50,
) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]], Optional[str]]:

    await start_client()

    # Проверяем, является ли это ID канала (число) или username
    identifier = raw_username.strip()
    is_channel_id = False
    channel_id = None  # Инициализируем для избежания NameError
    
    # ID канала - это число (может начинаться с минуса для супергрупп/каналов)
    if identifier.lstrip('-').isdigit():
        is_channel_id = True
        channel_id = int(identifier)
    else:
        username = _normalize_username(raw_username)
        if not username:
            return None, None, "Некорректный username"

    try:
        if is_channel_id:
            # Получаем entity по ID
            entity = await _with_retries(lambda: client.get_entity(channel_id))
        else:
            # Получаем entity по username
            entity = await _with_retries(lambda: client.get_entity(f"https://t.me/{username}"))
    except (UsernameInvalidError, UsernameNotOccupiedError):
        return None, None, "Такого username не существует"
    except (ChannelInvalidError, ChannelPrivateError):
        return None, None, "Канал приватный или невалидный"
    except FloodWaitError as e:
        return None, None, f"FloodWait: ждать {e.seconds} сек"
    except RPCError as e:
        return None, None, f"RPCError: {e}"
    except Exception as e:
        return None, None, f"Ошибка: {type(e).__name__}: {e}"

    if not getattr(entity, "broadcast", False):
        return None, None, "Это не канал"

    # Логируем полученный entity для отладки
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info(f"Entity received: id={entity.id}, username={entity.username}, title={getattr(entity, 'title', None)}")

    about = ""
    subs = 0

    try:
        full_channel = await _with_retries(lambda: client(GetFullChannelRequest(entity)))
        if full_channel and hasattr(full_channel, "full_chat"):
            about = getattr(full_channel.full_chat, "about", "") or ""
            subs = getattr(full_channel.full_chat, "participants_count", 0) or 0
    except Exception:
        pass

    # Для ID-based каналов используем оригинальный переданный ID, а не entity.id
    # Telethon возвращает entity.id без префикса -100 для каналов
    if is_channel_id and channel_id is not None:
        actual_id = channel_id
    else:
        actual_id = entity.id
    
    channel_data = {
        "id": actual_id,
        "title": getattr(entity, "title", None),
        "username": entity.username,
        "about": about,
        "participants_count": subs,
    }

    try:
        messages = await _with_retries(lambda: client.get_messages(entity, limit=limit))
    except Exception as e:
        return channel_data, [], f"Ошибка получения постов: {e}"

    posts: List[Dict[str, Any]] = []

    for m in messages:
        if not m.message:
            continue

        fwd_id = None
        if m.fwd_from and getattr(m.fwd_from.from_id, "channel_id", None):
            fwd_id = m.fwd_from.from_id.channel_id

        posts.append(
            {
                "date": m.date,
                "views": m.views or 0,
                "forwards": m.forwards or 0,
                "text": m.message,
                "forwarded_from_id": fwd_id,
            }
        )

    return channel_data, posts, None
