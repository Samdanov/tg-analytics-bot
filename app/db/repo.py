import asyncpg
from typing import Optional, List, Dict, Any

from app.core.config import config
from datetime import datetime

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = config.postgres_dsn

        # asyncpg не понимает "postgresql+asyncpg://", ему нужен "postgresql://"
        if dsn.startswith("postgresql+asyncpg://"):
            dsn = "postgresql://" + dsn.split("postgresql+asyncpg://", 1)[1]

        # На всякий случай можно ещё postgres+asyncpg обработать
        if dsn.startswith("postgres+asyncpg://"):
            dsn = "postgres://" + dsn.split("postgres+asyncpg://", 1)[1]

        _pool = await asyncpg.create_pool(dsn=dsn)

    return _pool

async def save_channel(pool, channel_data):
    username = channel_data.get("username")
    if not username:
        raise ValueError("Не удалось определить username канала — невозможен анализ.")

    username = username.strip().lstrip("@")

    title = channel_data.get("title") or ""
    description = channel_data.get("description") or ""
    subscribers = channel_data.get("subscribers") or 0

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO channels (username, title, description, subscribers, last_update)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (username) DO UPDATE
            SET title = EXCLUDED.title,
                description = EXCLUDED.description,
                subscribers = EXCLUDED.subscribers,
                last_update = now()
            RETURNING id;
            """,
            username,
            title,
            description,
            subscribers
        )

    return row["id"]


async def save_posts(pool, channel_id: int, posts):
    if not posts:
        return

    query = """
        INSERT INTO posts (channel_id, date, views, forwards, text)
        VALUES ($1, $2, $3, $4, $5)
    """

    async with pool.acquire() as conn:
        async with conn.transaction():
            for p in posts:
                # 🩹 FIX: делаем datetime "naive" → без tzinfo
                dt = p["date"]
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)

                await conn.execute(
                    query,
                    channel_id,
                    dt,
                    p.get("views", 0),
                    p.get("forwards", 0),
                    p.get("text", ""),
                )
