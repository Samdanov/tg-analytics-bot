"""
Post Repository

Репозиторий для работы с постами каналов.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, delete

from .base import BaseRepository
from app.db.models import Post
from app.db.database import async_session_maker
from app.core.logging import get_logger

logger = get_logger(__name__)


class PostRepository(BaseRepository[Post]):
    """
    Репозиторий для работы с постами.
    
    Предоставляет методы для:
    - CRUD операций
    - Получения постов канала
    - Массовой замены постов
    - Статистики по постам
    """
    
    def __init__(self):
        super().__init__(Post)
    
    async def get_by_channel(
        self,
        channel_id: int,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Post]:
        """
        Получить посты канала.
        
        Args:
            channel_id: ID канала
            limit: Максимальное количество
            offset: Сдвиг
        
        Returns:
            Список постов, отсортированных по дате (новые первые)
        """
        async with async_session_maker() as session:
            query = select(Post).where(
                Post.channel_id == channel_id
            ).order_by(Post.date.desc())
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def replace_posts(
        self,
        channel_id: int,
        posts_data: List[dict]
    ) -> int:
        """
        Полностью заменить посты канала новыми.
        
        Args:
            channel_id: ID канала
            posts_data: Список словарей с данными постов
        
        Returns:
            Количество сохраненных постов
        """
        if not posts_data:
            return 0
        
        async with async_session_maker() as session:
            # Удаляем старые посты
            await session.execute(
                delete(Post).where(Post.channel_id == channel_id)
            )
            
            # Создаем новые
            new_posts = []
            for p_data in posts_data:
                # Нормализуем datetime (убираем timezone)
                dt = p_data["date"]
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                
                post = Post(
                    channel_id=channel_id,
                    date=dt,
                    views=p_data.get("views", 0),
                    forwards=p_data.get("forwards", 0),
                    text=p_data.get("text", ""),
                )
                new_posts.append(post)
            
            session.add_all(new_posts)
            await session.commit()
            
            logger.debug(f"Posts replaced for channel_id={channel_id}, count={len(new_posts)}")
            return len(new_posts)
    
    async def count_by_channel(self, channel_id: int) -> int:
        """
        Подсчитать количество постов канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            Количество постов
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            result = await session.execute(
                select(func.count()).select_from(Post).where(
                    Post.channel_id == channel_id
                )
            )
            return result.scalar_one()
    
    async def get_posts_stats(self, channel_id: int) -> dict:
        """
        Получить статистику по постам канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            Словарь со статистикой:
            - total_posts: общее количество
            - avg_views: средние просмотры
            - avg_forwards: средние пересылки
            - total_views: всего просмотров
            - total_forwards: всего пересылок
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            
            result = await session.execute(
                select(
                    func.count(Post.id).label("total"),
                    func.avg(Post.views).label("avg_views"),
                    func.avg(Post.forwards).label("avg_forwards"),
                    func.sum(Post.views).label("total_views"),
                    func.sum(Post.forwards).label("total_forwards"),
                ).where(Post.channel_id == channel_id)
            )
            
            row = result.first()
            
            return {
                "total_posts": row.total or 0,
                "avg_views": float(row.avg_views or 0),
                "avg_forwards": float(row.avg_forwards or 0),
                "total_views": row.total_views or 0,
                "total_forwards": row.total_forwards or 0,
            }
    
    async def delete_by_channel(self, channel_id: int) -> int:
        """
        Удалить все посты канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            Количество удаленных постов
        """
        async with async_session_maker() as session:
            result = await session.execute(
                delete(Post).where(Post.channel_id == channel_id)
            )
            await session.commit()
            
            count = result.rowcount
            logger.debug(f"Deleted {count} posts for channel_id={channel_id}")
            return count
    
    async def get_posts_with_text(
        self,
        channel_id: int,
        min_length: int = 10,
        limit: Optional[int] = None
    ) -> List[Post]:
        """
        Получить посты с текстом (не пустые).
        
        Args:
            channel_id: ID канала
            min_length: Минимальная длина текста
            limit: Максимальное количество
        
        Returns:
            Список постов с текстом
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            
            query = select(Post).where(
                Post.channel_id == channel_id,
                func.length(Post.text) >= min_length
            ).order_by(Post.date.desc())
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())

