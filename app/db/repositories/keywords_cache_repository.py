"""
Keywords Cache Repository

Репозиторий для работы с кешем ключевых слов (результаты LLM анализа).
"""

import json
from datetime import datetime
from typing import Optional
from sqlalchemy import select

from .base import BaseRepository
from app.db.models import KeywordsCache
from app.db.database import async_session_maker
from app.schemas import AnalysisResultSchema
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeywordsCacheRepository(BaseRepository[KeywordsCache]):
    """
    Репозиторий для работы с кешем keywords (результаты LLM).
    
    KeywordsCache хранит:
    - audience (целевая аудитория)
    - tone (тональность)
    - keywords_json (ключевые слова в JSON)
    """
    
    def __init__(self):
        super().__init__(KeywordsCache)
    
    async def get_by_channel_id(self, channel_id: int) -> Optional[KeywordsCache]:
        """
        Получить кеш по ID канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            KeywordsCache или None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(KeywordsCache).where(
                    KeywordsCache.channel_id == channel_id
                )
            )
            return result.scalar_one_or_none()
    
    async def upsert_analysis(
        self,
        channel_id: int,
        analysis: AnalysisResultSchema
    ) -> KeywordsCache:
        """
        UPSERT результатов анализа.
        
        Args:
            channel_id: ID канала
            analysis: AnalysisResultSchema с результатами
        
        Returns:
            KeywordsCache (созданный или обновленный)
        """
        keywords_json = json.dumps(analysis.keywords, ensure_ascii=False)
        
        async with async_session_maker() as session:
            # Проверяем существование
            existing = await session.get(KeywordsCache, channel_id)
            
            if existing:
                # Обновляем
                existing.audience = analysis.audience
                existing.tone = analysis.tone
                existing.keywords_json = keywords_json
                existing.created_at = datetime.utcnow()
                cache = existing
            else:
                # Создаем
                cache = KeywordsCache(
                    channel_id=channel_id,
                    audience=analysis.audience,
                    tone=analysis.tone,
                    keywords_json=keywords_json,
                    created_at=datetime.utcnow(),
                )
                session.add(cache)
            
            await session.commit()
            await session.refresh(cache)
            
            logger.debug(f"Keywords cache upserted for channel_id={channel_id}")
            return cache
    
    async def get_keywords_list(self, channel_id: int) -> list:
        """
        Получить список ключевых слов канала.
        
        Args:
            channel_id: ID канала
        
        Returns:
            Список keywords или пустой список
        """
        cache = await self.get_by_channel_id(channel_id)
        if not cache or not cache.keywords_json:
            return []
        
        try:
            return json.loads(cache.keywords_json)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in keywords_cache for channel_id={channel_id}")
            return []
    
    def to_schema(self, cache: KeywordsCache) -> AnalysisResultSchema:
        """
        Преобразовать ORM модель в Pydantic schema.
        
        Args:
            cache: KeywordsCache ORM модель
        
        Returns:
            AnalysisResultSchema
        """
        keywords = []
        if cache.keywords_json:
            try:
                keywords = json.loads(cache.keywords_json)
            except json.JSONDecodeError:
                pass
        
        return AnalysisResultSchema(
            audience=cache.audience or "",
            keywords=keywords,
            tone=cache.tone or "",
            source="llm",  # Предполагаем что из LLM
            confidence=1.0
        )

