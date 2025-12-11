# app/services/similarity_engine/engine.py

import json
from datetime import datetime
from typing import List, Tuple, Dict, Set

from sqlalchemy import delete
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.db.database import async_session_maker
from app.db.models import AnalyticsResults
from app.services.similarity_engine.shared import (
    load_keywords_corpus,
    is_noise_channel,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class SimilarityEngine:
    def __init__(self, top_n: int = 10, max_df_ratio: float = 0.3, min_keywords_per_channel: int = 4):
        self.top_n = top_n
        self.max_df_ratio = max_df_ratio
        self.min_keywords_per_channel = min_keywords_per_channel

    async def _prepare_corpus(self) -> Tuple[List[int], List[str]]:
        raw_tokens_by_channel, meta_by_channel = await load_keywords_corpus()

        # Отбрасываем шумовые каналы (для всех, не только таргета)
        filtered: Dict[int, List[str]] = {}
        for cid, tokens in raw_tokens_by_channel.items():
            meta = meta_by_channel.get(cid, {})
            if is_noise_channel(meta.get("username"), meta.get("title"), tokens):
                continue
            filtered[cid] = tokens

        if len(filtered) < 2:
            return [], []

        # DF фильтр
        df: Dict[str, int] = {}
        for tokens in filtered.values():
            unique = set(tokens)
            for t in unique:
                df[t] = df.get(t, 0) + 1

        num_docs = len(filtered)
        frequent_tokens: Set[str] = {
            t for t, count in df.items() if count / num_docs > self.max_df_ratio
        }

        ids: List[int] = []
        docs: List[str] = []
        for cid, tokens in filtered.items():
            cleaned = [t for t in tokens if t not in frequent_tokens]
            if len(cleaned) < self.min_keywords_per_channel:
                continue
            ids.append(cid)
            docs.append(" ".join(cleaned))

        if len(ids) < 2:
            return [], []

        return ids, docs

    async def calculate_similarity(self):
        logger.info("[ENGINE] загрузка данных…")

        ids, docs = await self._prepare_corpus()

        if len(ids) < 2:
            logger.warning("[ENGINE] недостаточно каналов для similarity")
            return

        logger.info("[ENGINE] каналов для анализа: %s", len(ids))

        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(docs)

        sim = cosine_similarity(X)

        logger.info("[ENGINE] считаю похожесть…")
        results = []

        for idx, cid in enumerate(ids):
            scores = sim[idx]

            pairs = [
                (ids[j], float(scores[j]))
                for j in range(len(ids))
                if j != idx
            ]

            pairs.sort(key=lambda x: x[1], reverse=True)
            pairs = pairs[: self.top_n]

            results.append((cid, pairs))

        logger.info("[ENGINE] сохраняю результаты…")

        async with async_session_maker() as session:
            # удаляем только для присутствующих каналов, не весь AnalyticsResults
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id.in_(ids))
            )

            for cid, similar in results:
                payload = json.dumps(
                    [{"channel_id": ch, "score": sc} for ch, sc in similar],
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
