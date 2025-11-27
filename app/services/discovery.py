import asyncio
from telethon.tl.types import Channel
from telethon.errors import FloodWaitError, RPCError

from app.services.telegram_parser.client import client
from app.db.repo import get_pool


class ChannelDiscovery:
    """
    Ищет каналы по словам через search_global.
    Возвращает список username каналов.
    """

    async def search_topic(self, topic: str, limit: int = 50) -> list[str]:
        usernames: set[str] = set()

        try:
            results = await client.search_global(topic)

            for item in results:
                if isinstance(item, Channel) and getattr(item, "username", None):
                    usernames.add(item.username.lower())
                    if len(usernames) >= limit:
                        break

        except FloodWaitError as e:
            print(f"[FLOOD] Ждём {e.seconds} сек (topic={topic})")
            await asyncio.sleep(e.seconds)
            return await self.search_topic(topic, limit)

        except RPCError as e:
            print(f"[RPC ERROR] {e} (topic={topic})")

        return list(usernames)


async def save_usernames_to_db(usernames: list[str]) -> None:
    """
    Сохраняем username в таблицу channels, без дублей.
    """
    if not usernames:
        return

    pool = await get_pool()
    query = """
        INSERT INTO channels (username)
        VALUES ($1)
        ON CONFLICT (username) DO NOTHING
    """

    async with pool.acquire() as conn:
        async with conn.transaction():
            for u in usernames:
                await conn.execute(query, u)
