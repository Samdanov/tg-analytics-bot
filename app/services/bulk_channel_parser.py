import asyncio
from datetime import datetime
from app.db.database import async_session_maker
from app.db.models import Channels, Posts
from sqlalchemy import select, delete
from app.services.telegram_parser.channel_info import get_channel_with_posts


class BulkChannelParser:

    def __init__(self, post_limit: int = 50):
        self.post_limit = post_limit

    async def get_all_usernames(self):
        async with async_session_maker() as session:
            query = select(Channels.id, Channels.username)
            rows = await session.execute(query)
            return rows.all()

    async def parse_one(self, channel_id: int, username: str):
        print(f"[PARSE] {username}")

        info, posts, error = await get_channel_with_posts(username, limit=self.post_limit)

        if error:
            print(f"[ERROR] {username}: {error}")
            return False

        async with async_session_maker() as session:

            # очистим старые посты, чтобы не плодить дубли
            await session.execute(
                delete(Posts).where(Posts.channel_id == channel_id)
            )

            # обновление информации о канале
            await session.execute(
                Channels.__table__.update()
                .where(Channels.id == channel_id)
                .values(
                    title=info["title"],
                    description=info["about"],
                    subscribers=info["participants_count"],
                    updated_at=datetime.utcnow(),
                )
            )

            # добавление постов
            for p in posts:
                session.add(
                    Posts(
                        channel_id=channel_id,
                        text=p["text"],
                        date=p["date"],
                        views=p["views"],
                        forwards=p["forwards"],
                    )
                )

            await session.commit()

        print(f"[OK] {username}")
        return True

    async def parse_all(self):
        channels = await self.get_all_usernames()

        print(f"[INFO] Найдено {len(channels)} каналов для массового парсинга.")

        for i, (channel_id, username) in enumerate(channels, start=1):
            print(f"[{i}/{len(channels)}] {username}")

            await self.parse_one(channel_id, username)

            await asyncio.sleep(1.2)   # анти-флуд, обязательно!

        print("[DONE] Массовый парсинг завершён.")
