# app/services/similarity_engine/website_similarity.py

"""
Поиск похожих каналов по ключевым словам из веб-сайта.
Без сохранения сайта в БД - работает напрямую с ключевыми словами.
"""

import json
from typing import List, Dict, Tuple
from math import log, sqrt

from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
from app.services.similarity_engine.shared import normalize_text, should_exclude_category
from app.core.logging import get_logger

logger = get_logger(__name__)


async def find_similar_channels_by_keywords(
    keywords: List[str],
    top_n: int = 10,
    min_keywords_match: int = 2
) -> List[Dict]:
    """
    Находит похожие каналы по ключевым словам из сайта.
    
    Args:
        keywords: Список ключевых слов из анализа сайта
        top_n: Количество похожих каналов
        min_keywords_match: Минимальное количество совпадений ключевых слов
    
    Returns:
        Список словарей: [{"channel_id": int, "score": float, "username": str, "title": str}, ...]
    """
    if not keywords:
        logger.warning("No keywords provided for similarity search")
        return []
    
    # Нормализуем ключевые слова
    normalized_keywords = set()
    for kw in keywords:
        norm = normalize_text(str(kw))
        if norm:
            for t in norm.split():
                if len(t) >= 3 and not t.isdigit():
                    normalized_keywords.add(t)
    
    if not normalized_keywords:
        logger.warning("No valid keywords after normalization")
        return []
    
    logger.info(f"Searching similar channels for {len(normalized_keywords)} keywords")
    
    # Загружаем все каналы с ключевыми словами
    async with async_session_maker() as session:
        q = (
            select(
                Channel.id,
                Channel.username,
                Channel.title,
                Channel.subscribers,
                Channel.category,
                KeywordsCache.keywords_json,
            )
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        rows = (await session.execute(q)).all()
    
    # Вычисляем схожесть для каждого канала
    similarities = []
    
    for channel_id, username, title, subscribers, category, kw_json in rows:
        if not kw_json:
            continue
        
        # Пропускаем исключённые категории (Блоги, Цитаты, etc.)
        if should_exclude_category(category):
            continue
        
        try:
            channel_keywords = json.loads(kw_json)
        except Exception:
            continue
        
        if not isinstance(channel_keywords, list) or not channel_keywords:
            continue
        
        # Нормализуем ключевые слова канала
        channel_tokens = set()
        for kw in channel_keywords:
            norm = normalize_text(str(kw))
            if norm:
                for t in norm.split():
                    if len(t) >= 3 and not t.isdigit():
                        channel_tokens.add(t)
        
        if not channel_tokens:
            continue
        
        # Вычисляем пересечение ключевых слов
        common = normalized_keywords.intersection(channel_tokens)
        
        if len(common) < min_keywords_match:
            continue
        
        # Вычисляем score (TF-IDF упрощенный)
        # Используем количество совпадений и их важность
        score = len(common) / sqrt(len(normalized_keywords) * len(channel_tokens))
        
        similarities.append({
            "channel_id": channel_id,
            "score": score,
            "username": username or f"id:{channel_id}",
            "title": title,
            "subscribers": subscribers,
            "matches": len(common)
        })
    
    # Сортируем по score
    similarities.sort(key=lambda x: x["score"], reverse=True)
    
    # Ограничиваем top_n
    result = similarities[:top_n]
    
    logger.info(f"Found {len(result)} similar channels")
    return result
