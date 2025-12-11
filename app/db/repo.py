from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete

from app.db.database import async_session_maker
from app.db.models import Channel, Post
from app.core.logging import get_logger

logger = get_logger(__name__)


async def save_channel(channel_data: Dict[str, Any]) -> int:
    """
    UPSERT канала через SQLAlchemy.
    Принимает данные так же, как раньше: about/description, participants_count/subscribers.
    """
    username = channel_data.get("username")
    if not username:
        raise ValueError("Не удалось определить username канала — невозможен анализ.")

    username = username.strip().lstrip("@")

    title = channel_data.get("title") or ""
    description = channel_data.get("about") or channel_data.get("description") or ""
    subscribers = channel_data.get("participants_count") or channel_data.get("subscribers") or 0

    async with async_session_maker() as session:
        result = await session.execute(select(Channel).where(Channel.username == username))
        channel = result.scalar_one_or_none()

        if channel:
            channel.title = title
            channel.description = description
            channel.subscribers = subscribers
            channel.last_update = datetime.utcnow()
            logger.debug("Channel updated username=%s id=%s", username, channel.id)
        else:
            channel = Channel(
                username=username,
                title=title,
                description=description,
                subscribers=subscribers,
                last_update=datetime.utcnow(),
            )
            session.add(channel)
            logger.debug("Channel inserted username=%s", username)

        await session.flush()
        channel_id = channel.id
        await session.commit()

    return channel_id


async def save_posts(channel_id: int, posts: List[Dict[str, Any]]) -> None:
    """
    Полностью заменяет посты канала новыми, как и прежняя версия.
    """
    if not posts:
        return

    async with async_session_maker() as session:
        await session.execute(delete(Post).where(Post.channel_id == channel_id))

        new_posts = []
        for p in posts:
            dt = p["date"]
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            new_posts.append(
                Post(
                    channel_id=channel_id,
                    date=dt,
                    views=p.get("views", 0),
                    forwards=p.get("forwards", 0),
                    text=p.get("text", ""),
                )
            )

        session.add_all(new_posts)
        await session.commit()

    logger.debug("Posts replaced channel_id=%s count=%s", channel_id, len(posts))


async def get_channel_id_by_username(username: str) -> Optional[int]:
    """
    Находит ID канала по username или возвращает None.
    """
    if not username:
        return None

    username = username.strip().lstrip("@")

    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel.id).where(Channel.username == username)
        )
        row = result.first()

    return row[0] if row else None
