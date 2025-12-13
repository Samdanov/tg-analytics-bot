"""
Analytics Results Repository

Репозиторий для работы с результатами similarity анализа.
"""

import json
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, delete

from .base import BaseRepository
from app.db.models import AnalyticsResults
from app.db.database import async_session_maker
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnalyticsResultsRepository(BaseRepository[AnalyticsResults]):
    """
    Репозиторий для работы с результатами similarity.
    
    AnalyticsResults хранит:
    - similar_channels_json (список похожих каналов с scores)
    """
    
    def __init__(self):
        super().__init__(AnalyticsResults)
    
    async def get_by_channel_id(self, channel_id: int) -> Optional[AnalyticsResults]:
        """
        Получить результаты по ID канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            AnalyticsResults или None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(AnalyticsResults).where(
                    AnalyticsResults.channel_id == channel_id
                )
            )
            return result.scalar_one_or_none()
    
    async def upsert_results(
        self,
        channel_id: int,
        similar_channels: List[Tuple[int, float]]
    ) -> AnalyticsResults:
        """
        UPSERT результатов similarity.
        
        Args:
            channel_id: ID целевого канала
            similar_channels: Список (channel_id, score)
        
        Returns:
            AnalyticsResults (созданный или обновленный)
        """
        # Преобразуем в JSON
        payload = json.dumps(
            [{"channel_id": cid, "score": score} for cid, score in similar_channels],
            ensure_ascii=False
        )
        
        async with async_session_maker() as session:
            # Удаляем старые результаты
            await session.execute(
                delete(AnalyticsResults).where(
                    AnalyticsResults.channel_id == channel_id
                )
            )
            
            # Создаем новые
            result = AnalyticsResults(
                channel_id=channel_id,
                similar_channels_json=payload,
                created_at=datetime.utcnow()
            )
            session.add(result)
            await session.commit()
            await session.refresh(result)
            
            logger.debug(f"Analytics results upserted for channel_id={channel_id}, count={len(similar_channels)}")
            return result
    
    async def get_similar_channels(
        self,
        channel_id: int,
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        Получить список похожих каналов.
        
        Args:
            channel_id: ID канала
            limit: Максимальное количество (если None - все)
        
        Returns:
            Список словарей [{"channel_id": int, "score": float}, ...]
        """
        result = await self.get_by_channel_id(channel_id)
        if not result or not result.similar_channels_json:
            return []
        
        try:
            channels = json.loads(result.similar_channels_json)
            if limit:
                return channels[:limit]
            return channels
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in analytics_results for channel_id={channel_id}")
            return []
    
    async def get_top_similar(
        self,
        channel_id: int,
        top_n: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Получить топ-N похожих каналов.
        
        Args:
            channel_id: ID канала
            top_n: Количество топовых каналов
        
        Returns:
            Список (channel_id, score)
        """
        channels = await self.get_similar_channels(channel_id, limit=top_n)
        return [(ch["channel_id"], ch["score"]) for ch in channels]
    
    async def has_results(self, channel_id: int) -> bool:
        """
        Проверить, есть ли результаты для канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            True если есть результаты
        """
        result = await self.get_by_channel_id(channel_id)
        if not result:
            return False
        
        channels = await self.get_similar_channels(channel_id)
        return len(channels) > 0
    
    async def delete_by_channel(self, channel_id: int) -> bool:
        """
        Удалить результаты для канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            True если удалено
        """
        async with async_session_maker() as session:
            result = await session.execute(
                delete(AnalyticsResults).where(
                    AnalyticsResults.channel_id == channel_id
                )
            )
            await session.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"Analytics results deleted for channel_id={channel_id}")
            return deleted

