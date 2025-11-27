import asyncio
from datetime import datetime

from telethon.errors import (
    UsernameNotOccupiedError,
    UsernameInvalidError,
    FloodWaitError,
    ChannelInvalidError,
    ChannelPrivateError,
    RPCError
)

from app.services.telegram_parser.client import client
from app.services.telegram_parser.channel_info import get_channel_with_posts
from app.db.repo import get_pool


class BulkChannelParser:
    def __init__(self, post_limit: int = 50, pause: float = 0.4):
        self.post_limit = post_limit
        self.pause = pause

    async def _get_entity(self, username: str):
        """
        Безопасное получение канала через get_entity.
        Полная замена ResolveUsernameRequest.
        """
        if not username or len(username) < 4 or len(username) > 32:
            return None

        try:
            return await client.get_entity(f"https://t.me/{username}")
        except (UsernameInvalidError, UsernameNotOccupiedError):
            return None
        except (ChannelInvalidError, ChannelPrivateError):
            return None
        except FloodWaitError as e:
            print(f"[FLOOD] пропускаем @{username}, ждать {e.seconds} сек")
            return None
        except RPCError:
            return None
        except Exception:
            return None

    async def _get_all_channels(self):
        pool = await get_pool()
        query = "SELECT id, username FROM channels ORDER BY id"

        async with pool.acquire() as conn:
            return await conn.fetch(query)

    async def _parse_one(self, channel_id: int, username: str):
        print(f"[PARSE] @{username}")

        entity = await self._get_entity(username)
        if not entity:
            print(f"[SKIP] @{username} не найден/удалён/приватный")
            return

        # Получаем полную инфу через get_full_info
        info, posts, error = await get_channel_with_posts(username, limit=self.post_limit)

        if error:
            print(f"[ERROR] @{username}: {error}")
            return

        pool = await get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():

                # Обновление инфы о канале
                await conn.execute(
                    """
                    UPDATE channels
                    SET title=$1,
                        description=$2,
                        subscribers=$3,
                        updated_at=NOW()
                    WHERE id=$4
                    """,
                    info["title"],
                    info["about"],
                    info["participants_count"],
                    channel_id
                )

                # Удаляем старые посты
                await conn.execute("DELETE FROM posts WHERE channel_id=$1", channel_id)

                # Вставляем новые посты
                insert_q = """
                    INSERT INTO posts (channel_id, date, views, forwards, text)
                    VALUES ($1, $2, $3, $4, $5)
                """

                for p in posts:
                    dt = p["date"]
                    if hasattr(dt, "tzinfo") and dt.tzinfo:
                        dt = dt.replace(tzinfo=None)

                    await conn.execute(
                        insert_q,
                        channel_id,
                        dt,
                        p.get("views", 0),
                        p.get("forwards", 0),
                        p.get("text", "")
                    )

        print(f"[OK] @{username}")

    async def parse_all(self):
        channels = await self._get_all_channels()
        total = len(channels)

        print(f"[INFO] Найдено {total} каналов для безопасного парсинга")

        for idx, row in enumerate(channels, start=1):
            username = row["username"]
            channel_id = row["id"]

            print(f"[{idx}/{total}] @{username}")
            await self._parse_one(channel_id, username)

            await asyncio.sleep(self.pause)

        print("[DONE] Парсинг завершён")
