"""
Channel Repository

Репозиторий для работы с каналами.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .base import BaseRepository
from app.db.models import Channel
from app.db.database import async_session_maker
from app.schemas import ChannelResponseSchema, ChannelCreateSchema, ChannelUpdateSchema
from app.domain import ChannelIdentifier
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChannelRepository(BaseRepository[Channel]):
    """
    Репозиторий для работы с каналами.
    
    Предоставляет методы для:
    - CRUD операций
    - Поиска по username/ID
    - UPSERT операций
    - Получения каналов с keywords
    """
    
    def __init__(self):
        super().__init__(Channel)
    
    async def get_by_username(self, username: str) -> Optional[Channel]:
        """
        Получить канал по username.
        
        Args:
            username: Username канала (нормализованный, без @)
        
        Returns:
            Channel или None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(Channel).where(Channel.username == username)
            )
            return result.scalar_one_or_none()
    
    async def get_by_identifier(self, identifier: ChannelIdentifier) -> Optional[Channel]:
        """
        Получить канал по идентификатору (domain object).
        
        Args:
            identifier: ChannelIdentifier из domain layer
        
        Returns:
            Channel или None
        """
        db_value = identifier.to_db_format()
        return await self.get_by_username(db_value)
    
    async def upsert(self, data: ChannelCreateSchema) -> Channel:
        """
        UPSERT канала (создать или обновить).
        
        Args:
            data: ChannelCreateSchema с данными
        
        Returns:
            Channel (созданный или обновленный)
        """
        # Нормализуем identifier
        identifier = ChannelIdentifier.from_raw(data.identifier)
        username = identifier.to_db_format()
        
        async with async_session_maker() as session:
            # UPSERT через PostgreSQL
            insert_stmt = insert(Channel).values(
                username=username,
                title=data.title or identifier.to_display_format(),
                description=data.description or "",
                subscribers=data.subscribers,
                last_update=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            
            on_conflict_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Channel.username],
                set_=dict(
                    title=insert_stmt.excluded.title,
                    description=insert_stmt.excluded.description,
                    subscribers=insert_stmt.excluded.subscribers,
                    last_update=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                ),
            ).returning(Channel.id)
            
            result = await session.execute(on_conflict_stmt)
            channel_id = result.scalar_one()
            await session.commit()
            
            # Получаем полный объект
            channel = await session.get(Channel, channel_id)
            await session.refresh(channel)
            
            logger.debug(f"Channel upserted: username={username}, id={channel_id}")
            return channel
    
    async def update_metadata(
        self,
        channel_id: int,
        update_data: ChannelUpdateSchema
    ) -> Optional[Channel]:
        """
        Обновить метаданные канала.
        
        Args:
            channel_id: ID канала
            update_data: ChannelUpdateSchema с изменениями
        
        Returns:
            Обновленный Channel или None
        """
        update_dict = update_data.model_dump(exclude_none=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        return await self.update(channel_id, **update_dict)
    
    async def update_keywords(
        self,
        channel_id: int,
        keywords: List[str]
    ) -> Optional[Channel]:
        """
        Обновить ключевые слова канала.
        
        Args:
            channel_id: ID канала
            keywords: Список ключевых слов
        
        Returns:
            Обновленный Channel или None
        """
        return await self.update(
            channel_id,
            keywords=keywords,
            last_update=datetime.utcnow()
        )
    
    async def get_with_keywords(
        self,
        limit: Optional[int] = None,
        min_keywords: int = 1
    ) -> List[Channel]:
        """
        Получить каналы с ключевыми словами.
        
        Args:
            limit: Максимальное количество
            min_keywords: Минимальное количество keywords
        
        Returns:
            Список каналов с keywords
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            
            query = select(Channel).where(
                func.array_length(Channel.keywords, 1) >= min_keywords
            )
            
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def search_by_title(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[Channel]:
        """
        Поиск каналов по названию.
        
        Args:
            search_term: Поисковый запрос
            limit: Максимальное количество результатов
        
        Returns:
            Список найденных каналов
        """
        async with async_session_maker() as session:
            query = select(Channel).where(
                Channel.title.ilike(f"%{search_term}%")
            ).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_recently_updated(
        self,
        limit: int = 10
    ) -> List[Channel]:
        """
        Получить недавно обновленные каналы.
        
        Args:
            limit: Количество каналов
        
        Returns:
            Список каналов, отсортированных по дате обновления
        """
        async with async_session_maker() as session:
            query = select(Channel).where(
                Channel.last_update.isnot(None)
            ).order_by(
                Channel.last_update.desc()
            ).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    # Преобразование в schemas
    def to_schema(self, channel: Channel) -> ChannelResponseSchema:
        """
        Преобразовать ORM модель в Pydantic schema.
        
        Args:
            channel: Channel ORM модель
        
        Returns:
            ChannelResponseSchema
        """
        identifier = ChannelIdentifier.from_raw(channel.username)
        
        return ChannelResponseSchema(
            id=channel.id,
            identifier=channel.username,
            is_id_based=identifier.is_id_based,
            title=channel.title,
            description=channel.description,
            subscribers=channel.subscribers,
            keywords=channel.keywords or [],
            last_update=channel.last_update,
            created_at=None,  # Добавим поле в модель если нужно
            updated_at=channel.updated_at
        )

