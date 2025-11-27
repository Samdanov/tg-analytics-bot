from typing import Set

from app.db.repo import get_pool
from app.services.telegram_parser.client import client
from telethon import functions


class DiscoveryForwardsService:
    """
    Ищет каналы через пересланные сообщения.
    """

    async def get_forwarded_channel_ids(self) -> Set[int]:
        pool = await get_pool()

        query = """
            SELECT DISTINCT forwarded_from_id
            FROM posts
            WHERE forwarded_from_id IS NOT NULL
        """

        channel_ids = set()

        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

            for r in rows:
                cid = r["forwarded_from_id"]
                if cid:
                    channel_ids.add(cid)

        return channel_ids

    async def resolve_ids_to_usernames(self, ids: Set[int]) -> Set[str]:
        usernames = set()

        for cid in ids:
            try:
                result = await client(
                    functions.channels.GetChannelsRequest(id=[cid])
                )

                for ch in result.chats:
                    if ch.username:
                        usernames.add(ch.username.lower())

            except:
                pass  # не найден / приватный / ошибка API

        return usernames

    async def save_new_usernames(self, usernames: Set[str]) -> int:
        pool = await get_pool()
        added = 0

        insert_q = """
            INSERT INTO channels (username)
            VALUES ($1)
            ON CONFLICT (username) DO NOTHING
        """

        async with pool.acquire() as conn:
            async with conn.transaction():
                for u in usernames:
                    res = await conn.execute(insert_q, u)
                    if res == "INSERT 0 1":
                        added += 1

        return added
