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

    username = _normalize_username(raw_username)
    if not username:
        return None, None, "Некорректный username"

    try:
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

    try:
        full = await _with_retries(lambda: client.get_entity(entity))
    except Exception:
        full = None

    about = ""
    subs = 0

    if full and hasattr(full, "full_chat"):
        about = getattr(full.full_chat, "about", "") or ""
        subs = getattr(full.full_chat, "participants_count", 0) or 0

    channel_data = {
        "id": entity.id,
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
