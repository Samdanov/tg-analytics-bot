# app/services/similarity_engine/engine.py
"""
Batch-расчёт similarity ПО КАТЕГОРИЯМ.

АРХИТЕКТУРА:
- category = PRIMARY TOPIC (жёсткий фильтр)
- similarity считается ТОЛЬКО внутри одной категории
- каналы разных категорий НИКОГДА не сравниваются

ПОЧЕМУ ТАК:
- TF-IDF имеет смысл только внутри одной тематики
- IDF глобально = "бизнес" теряет вес везде
- IDF внутри категории = "налоги" важны в Бухгалтерии, не важны в IT
"""

import json
from datetime import datetime
from typing import List, Dict, Set
from collections import defaultdict
from math import log, sqrt

from sqlalchemy import delete

from app.db.database import async_session_maker
from app.db.models import AnalyticsResults
from app.services.similarity_engine.shared import load_keywords_corpus
from app.core.logging import get_logger

logger = get_logger(__name__)


class SimilarityEngine:
    """
    Batch-движок similarity ПО КАТЕГОРИЯМ.
    
    Правила:
    1. Каналы группируются по category
    2. TF-IDF считается ВНУТРИ каждой категории
    3. Similarity только между каналами ОДНОЙ категории
    4. Каналы без category → отдельная группа "unknown"
    """
    
    def __init__(
        self,
        top_n: int = 10,
        min_keywords: int = 3,
        min_channels_in_category: int = 5,
    ):
        """
        Args:
            top_n: Сколько похожих каналов возвращать
            min_keywords: Минимум keywords у канала для участия
            min_channels_in_category: Минимум каналов в категории для расчёта
        """
        self.top_n = top_n
        self.min_keywords = min_keywords
        self.min_channels_in_category = min_channels_in_category
    
    async def calculate_similarity(self):
        """
        Batch-расчёт similarity для всех каналов.
        
        Алгоритм:
        1. Загрузить все каналы с keywords
        2. Сгруппировать по category
        3. Для каждой категории: TF-IDF + similarity внутри
        4. Сохранить результаты
        """
        logger.info("[ENGINE] загрузка данных...")
        
        tokens_by_channel, meta_by_channel = await load_keywords_corpus(filter_noise=True)
        
        if not tokens_by_channel:
            logger.warning("[ENGINE] нет каналов для анализа")
            return
        
        # =====================================================
        # ГРУППИРОВКА ПО КАТЕГОРИЯМ
        # =====================================================
        channels_by_category: Dict[str, List[int]] = defaultdict(list)
        
        for cid in tokens_by_channel.keys():
            meta = meta_by_channel.get(cid, {})
            category = (meta.get("category") or "").strip().lower()
            
            # Пустая категория → "unknown"
            if not category:
                category = "unknown"
            
            channels_by_category[category].append(cid)
        
        logger.info("[ENGINE] категорий: %d, каналов: %d", 
                   len(channels_by_category), len(tokens_by_channel))
        
        # =====================================================
        # РАСЧЁТ SIMILARITY ВНУТРИ КАЖДОЙ КАТЕГОРИИ
        # =====================================================
        all_results: List[tuple] = []
        processed_categories = 0
        skipped_small = 0
        
        for category, channel_ids in channels_by_category.items():
            # Пропускаем слишком маленькие категории
            if len(channel_ids) < self.min_channels_in_category:
                skipped_small += 1
                continue
            
            # Собираем данные для этой категории
            category_tokens: Dict[int, List[str]] = {}
            for cid in channel_ids:
                tokens = tokens_by_channel.get(cid, [])
                if len(tokens) >= self.min_keywords:
                    category_tokens[cid] = tokens
            
            if len(category_tokens) < 2:
                skipped_small += 1
                continue
            
            # TF-IDF + Similarity ВНУТРИ категории
            category_results = self._calculate_within_category(category_tokens)
            all_results.extend(category_results)
            processed_categories += 1
        
        logger.info("[ENGINE] обработано категорий: %d, пропущено (мало каналов): %d",
                   processed_categories, skipped_small)
        
        # =====================================================
        # СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
        # =====================================================
        if not all_results:
            logger.warning("[ENGINE] нет результатов для сохранения")
            return
        
        logger.info("[ENGINE] сохраняю результаты для %d каналов...", len(all_results))
        
        async with async_session_maker() as session:
            # Удаляем старые результаты для обработанных каналов
            processed_ids = [cid for cid, _ in all_results]
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id.in_(processed_ids))
            )
            
            # Сохраняем новые
            for cid, similar in all_results:
                payload = json.dumps(
                    [{"channel_id": ch, "score": round(sc, 4)} for ch, sc in similar],
                    ensure_ascii=False
                )
                session.add(
                    AnalyticsResults(
                        channel_id=cid,
                        similar_channels_json=payload,
                        created_at=datetime.utcnow()
                    )
                )
            
            await session.commit()
        
        logger.info("[ENGINE] готово")
    
    def _calculate_within_category(
        self,
        tokens_by_channel: Dict[int, List[str]]
    ) -> List[tuple]:
        """
        Расчёт TF-IDF + Cosine Similarity ВНУТРИ одной категории.
        
        Args:
            tokens_by_channel: {channel_id: [token1, token2, ...]}
        
        Returns:
            [(channel_id, [(similar_id, score), ...]), ...]
        """
        channel_ids = list(tokens_by_channel.keys())
        num_docs = len(channel_ids)
        
        if num_docs < 2:
            return []
        
        # DF (Document Frequency) внутри категории
        df: Dict[str, int] = {}
        for tokens in tokens_by_channel.values():
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        
        # IDF внутри категории (без глобального фильтра!)
        idf: Dict[str, float] = {}
        for term, doc_freq in df.items():
            # Стандартная IDF формула
            idf[term] = log((num_docs + 1) / (doc_freq + 1)) + 1
        
        # TF-IDF векторы для каждого канала
        tfidf_vectors: Dict[int, Dict[str, float]] = {}
        norms: Dict[int, float] = {}
        
        for cid, tokens in tokens_by_channel.items():
            # TF (Term Frequency)
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            
            # TF-IDF
            tfidf = {t: tf_val * idf.get(t, 0) for t, tf_val in tf.items()}
            tfidf_vectors[cid] = tfidf
            
            # Норма для cosine
            norms[cid] = sqrt(sum(v ** 2 for v in tfidf.values())) or 1.0
        
        # Cosine Similarity (попарно, но только внутри категории)
        results: List[tuple] = []
        
        for i, cid in enumerate(channel_ids):
            target_vec = tfidf_vectors[cid]
            target_norm = norms[cid]
            target_terms = set(target_vec.keys())
            
            scores: List[tuple] = []
            
            for j, other_cid in enumerate(channel_ids):
                if i == j:
                    continue
                
                other_vec = tfidf_vectors[other_cid]
                other_norm = norms[other_cid]
                
                # Dot product (только общие термины)
                common = target_terms & set(other_vec.keys())
                if not common:
                    continue
                
                dot = sum(target_vec[t] * other_vec[t] for t in common)
                score = dot / (target_norm * other_norm)
                
                if score > 0:
                    scores.append((other_cid, score))
            
            # Сортируем и берём top_n
            scores.sort(key=lambda x: x[1], reverse=True)
            results.append((cid, scores[:self.top_n]))
        
        return results
