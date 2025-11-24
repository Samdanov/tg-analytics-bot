import asyncpg
from typing import Optional, List, Dict, Any

from core.config import config

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=config.postgres_dsn)
    return _pool


async def save_channel(pool: asyncpg.Pool, data: Dict[str, Any]) -> int:
    """
    Сохраняем канал в таблицу channels.
    Пока без проверки дублей — для MVP ок.
    """
    query = """
        INSERT INTO channels (username, title, description, subscribers)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """
    channel_id = await pool.fetchval(
        query,
        data.get("username"),
        data.get("title"),
        data.get("about"),
        data.get("participants_count"),
    )
    return channel_id


async def save_posts(pool: asyncpg.Pool, channel_id: int, posts: List[Dict[str, Any]]) -> None:
    """
    Сохраняем посты в таблицу posts.
    """
    if not posts:
        return

    query = """
        INSERT INTO posts (channel_id, date, views, forwards, text)
        VALUES ($1, $2, $3, $4, $5)
    """

    async with pool.acquire() as conn:
        async with conn.transaction():
            for p in posts:
                await conn.execute(
                    query,
                    channel_id,
                    p.get("date"),
                    p.get("views"),
                    p.get("forwards"),
                    p.get("text"),
                )
