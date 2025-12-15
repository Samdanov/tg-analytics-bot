# app/services/similarity_engine/engine_single.py
"""
Расчёт similarity для ОДНОГО канала.

АРХИТЕКТУРА:
- Берём category target-канала
- Загружаем ТОЛЬКО каналы той же категории
- TF-IDF + Cosine ВНУТРИ категории
- Каналы разных категорий НИКОГДА не сравниваются
"""

import json
from typing import List, Dict, Optional
from math import log, sqrt

from sqlalchemy import select, delete

from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_channel_category(channel_id: int) -> Optional[str]:
    """Получает category канала из БД."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel.category).where(Channel.id == channel_id)
        )
        row = result.scalar_one_or_none()
        if row:
            return (row or "").strip().lower()
        return None


async def load_channels_by_category(category: str) -> Dict[int, List[str]]:
    """
    Загружает все каналы указанной категории с их keywords.
    
    Returns:
        {channel_id: [token1, token2, ...]}
    """
    async with async_session_maker() as session:
        # Нормализуем категорию для поиска
        category_lower = category.strip().lower()
        
        q = (
            select(
                Channel.id,
                Channel.category,
                KeywordsCache.keywords_json,
            )
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        
        rows = (await session.execute(q)).all()
    
    tokens_by_channel: Dict[int, List[str]] = {}
    
    for cid, ch_category, kw_json in rows:
        # Фильтр по категории
        ch_cat_lower = (ch_category or "").strip().lower()
        if ch_cat_lower != category_lower:
            continue
        
        if not kw_json:
            continue
        
        try:
            keywords = json.loads(kw_json)
        except Exception:
            continue
        
        if not isinstance(keywords, list) or len(keywords) < 2:
            continue
        
        # Нормализация токенов
        tokens = [str(kw).lower().strip() for kw in keywords if kw]
        tokens = [t for t in tokens if len(t) >= 2]
        
        if tokens:
            tokens_by_channel[cid] = tokens
    
    return tokens_by_channel


async def calculate_similarity_for_channel(
    target_channel_id: int,
    top_n: int = 10,
    min_keywords: int = 2,
) -> bool:
    """
    Расчёт похожих каналов для одного channel_id.
    
    ВАЖНО: Similarity считается ТОЛЬКО внутри category target-канала!
    
    Args:
        target_channel_id: ID целевого канала
        top_n: Количество похожих каналов
        min_keywords: Минимум keywords для участия
    
    Returns:
        True если успешно, False если нет данных
    """
    logger.info("[SINGLE] target=%d", target_channel_id)
    
    # =========================================================
    # 1. ПОЛУЧАЕМ CATEGORY TARGET-КАНАЛА
    # =========================================================
    target_category = await get_channel_category(target_channel_id)
    
    if not target_category:
        logger.warning("[SINGLE] target=%d не найден или без category", target_channel_id)
        await _save_empty_result(target_channel_id)
        return False
    
    logger.info("[SINGLE] target=%d category='%s'", target_channel_id, target_category)
    
    # =========================================================
    # 2. ЗАГРУЖАЕМ ТОЛЬКО КАНАЛЫ ЭТОЙ ЖЕ КАТЕГОРИИ
    # =========================================================
    tokens_by_channel = await load_channels_by_category(target_category)
    
    if target_channel_id not in tokens_by_channel:
        logger.warning("[SINGLE] target=%d нет keywords", target_channel_id)
        await _save_empty_result(target_channel_id)
        return False
    
    # Фильтруем по min_keywords
    filtered: Dict[int, List[str]] = {
        cid: tokens 
        for cid, tokens in tokens_by_channel.items()
        if len(tokens) >= min_keywords
    }
    
    if target_channel_id not in filtered:
        logger.warning("[SINGLE] target=%d мало keywords", target_channel_id)
        await _save_empty_result(target_channel_id)
        return False
    
    num_channels = len(filtered)
    logger.info("[SINGLE] каналов в категории '%s': %d", target_category, num_channels)
    
    if num_channels < 2:
        logger.warning("[SINGLE] мало каналов в категории")
        await _save_empty_result(target_channel_id)
        return False
    
    # =========================================================
    # 3. TF-IDF ВНУТРИ КАТЕГОРИИ
    # =========================================================
    
    # DF (Document Frequency) - только внутри этой категории!
    df: Dict[str, int] = {}
    for tokens in filtered.values():
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1
    
    # IDF (внутри категории, без глобального фильтра!)
    idf: Dict[str, float] = {}
    for term, doc_freq in df.items():
        idf[term] = log((num_channels + 1) / (doc_freq + 1)) + 1
    
    # TF-IDF вектор для target
    target_tokens = filtered[target_channel_id]
    target_tf: Dict[str, int] = {}
    for t in target_tokens:
        target_tf[t] = target_tf.get(t, 0) + 1
    
    target_tfidf = {t: tf * idf.get(t, 0) for t, tf in target_tf.items()}
    target_norm = sqrt(sum(v ** 2 for v in target_tfidf.values())) or 1.0
    target_terms = set(target_tfidf.keys())
    
    # =========================================================
    # 4. COSINE SIMILARITY С КАНДИДАТАМИ
    # =========================================================
    scores: List[tuple] = []
    
    for cid, tokens in filtered.items():
        if cid == target_channel_id:
            continue
        
        # TF-IDF вектор для кандидата
        cand_tf: Dict[str, int] = {}
        for t in tokens:
            cand_tf[t] = cand_tf.get(t, 0) + 1
        
        cand_tfidf = {t: tf * idf.get(t, 0) for t, tf in cand_tf.items()}
        cand_norm = sqrt(sum(v ** 2 for v in cand_tfidf.values())) or 1.0
        
        # Общие термины
        common = target_terms & set(cand_tfidf.keys())
        if not common:
            continue
        
        # Cosine similarity
        dot = sum(target_tfidf[t] * cand_tfidf[t] for t in common)
        score = dot / (target_norm * cand_norm)
        
        if score > 0:
            scores.append((cid, score))
    
    # Сортируем и берём top_n
    scores.sort(key=lambda x: x[1], reverse=True)
    top_results = scores[:top_n]
    
    # =========================================================
    # 5. ЛОГИРОВАНИЕ
    # =========================================================
    if scores:
        logger.info(
            "[SINGLE] target=%d: найдено %d похожих, top score=%.3f",
            target_channel_id, len(scores), scores[0][1] if scores else 0
        )
    else:
        logger.info("[SINGLE] target=%d: нет похожих каналов", target_channel_id)
    
    # =========================================================
    # 6. СОХРАНЕНИЕ
    # =========================================================
    await _save_result(target_channel_id, top_results)
    
    return True


async def _save_empty_result(channel_id: int):
    """Сохраняет пустой результат."""
    async with async_session_maker() as session:
        await session.execute(
            delete(AnalyticsResults).where(AnalyticsResults.channel_id == channel_id)
        )
        session.add(
            AnalyticsResults(
                channel_id=channel_id,
                similar_channels_json=json.dumps([]),
            )
        )
        await session.commit()


async def _save_result(channel_id: int, results: List[tuple]):
    """Сохраняет результат similarity."""
    async with async_session_maker() as session:
        await session.execute(
            delete(AnalyticsResults).where(AnalyticsResults.channel_id == channel_id)
        )
        
        payload = json.dumps(
            [{"channel_id": cid, "score": round(score, 4)} for cid, score in results],
            ensure_ascii=False
        )
        
        session.add(
            AnalyticsResults(
                channel_id=channel_id,
                similar_channels_json=payload,
            )
        )
        await session.commit()
