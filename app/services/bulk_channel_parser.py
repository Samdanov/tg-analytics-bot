import asyncio
from datetime import datetime

from app.db.repo import get_pool
from app.services.telegram_parser.channel_info import get_channel_with_posts


class BulkChannelParser:
    def __init__(self, post_limit: int = 50):
        self.post_limit = post_limit

    async def _get_all_channels(self):
        pool = await get_pool()
        query = "SELECT id, username FROM channels ORDER BY id"

        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

        return rows

    async def _parse_one(self, channel_id: int, username: str) -> bool:
        print(f"[PARSE] @{username}")

        info, posts, error = await get_channel_with_posts(username, limit=self.post_limit)

        if error:
            print(f"[ERROR] @{username}: {error}")
            return False

        pool = await get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():
                # обновляем канал
                await conn.execute(
                    """
                    UPDATE channels
                    SET title = $1,
                        description = $2,
                        subscribers = $3,
                        updated_at = NOW()
                    WHERE id = $4
                    """,
                    info["title"],
                    info["about"],
                    info["participants_count"],
                    channel_id,
                )

                # удаляем старые посты, чтобы не плодить дубли
                await conn.execute(
                    "DELETE FROM posts WHERE channel_id = $1",
                    channel_id,
                )

                # добавляем новые посты
                insert_q = """
                    INSERT INTO posts (channel_id, date, views, forwards, text)
                    VALUES ($1, $2, $3, $4, $5)
                """

                for p in posts:
                    dt = p["date"]
                    # делаем naive datetime
                    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)

                    await conn.execute(
                        insert_q,
                        channel_id,
                        dt,
                        p.get("views", 0),
                        p.get("forwards", 0),
                        p.get("text", ""),
                    )

        print(f"[OK] @{username}")
        return True

    async def parse_all(self):
        channels = await self._get_all_channels()
        total = len(channels)
        print(f"[INFO] Найдено {total} каналов для массового парсинга")

        for idx, row in enumerate(channels, start=1):
            channel_id = row["id"]
            username = row["username"]

            print(f"[{idx}/{total}] @{username}")
            await self._parse_one(channel_id, username)

            await asyncio.sleep(1.2)  # анти-флуд

        print("[DONE] Массовый парсинг завершён")
