# app/services/similarity_engine/engine.py

import json
import re
import unicodedata
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import select, delete
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults


def normalize_text(text: str) -> str:
    """
    Мягкая нормализация:
    - убираем удвоенные пробелы
    - оставляем цифры, буквы, бренды, короткие токены
    - режем только явный мусор
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^0-9a-zа-яё\-]+", " ", text)  # оставляем дефис для брендов: chat-gpt, mid-journey
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SimilarityEngine:
    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    async def load_docs(self) -> Tuple[List[int], List[str]]:
        """
        Загружаем ВСЕ каналы, у которых есть keywords_cache.
        Нормализуем ключи так же, как в engine_single.
        """
        async with async_session_maker() as session:
            q = (
                select(Channel.id, KeywordsCache.keywords_json)
                .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
            )
            rows = (await session.execute(q)).all()

        ids = []
        docs = []

        for cid, kw_json in rows:
            if not kw_json:
                continue

            try:
                kws = json.loads(kw_json)
            except:
                continue

            if not isinstance(kws, list):
                continue

            tokens: List[str] = []
            for kw in kws:
                norm = normalize_text(str(kw))
                if not norm:
                    continue
                tokens.extend(norm.split())

            # если keywords полностью пустые — пропускаем
            if len(tokens) == 0:
                continue

            ids.append(cid)
            docs.append(" ".join(tokens))

        return ids, docs

    async def calculate_similarity(self):
        print("[ENGINE] Загружаю данные…")

        ids, docs = await self.load_docs()

        if len(ids) < 2:
            print("[ENGINE] Недостаточно каналов для similarity.")
            return

        print(f"[ENGINE] Каналов для анализа: {len(ids)}")

        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(docs)

        sim = cosine_similarity(X)

        print("[ENGINE] Считаю похожесть…")
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

        print("[ENGINE] Сохраняю результаты…")

        async with async_session_maker() as session:
            # Очищаем старые результаты
            await session.execute(delete(AnalyticsResults))

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

        print("[ENGINE] Готово!")
