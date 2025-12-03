# app/services/similarity_engine/engine_single.py

import json
from typing import List, Dict, Any

from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults


async def calculate_similarity_for_channel(target_channel_id: int, top_n: int = 10):
    """
    Считает похожие каналы ТОЛЬКО для одного канала.
    Работает даже при маленькой базе.
    """

    async with async_session_maker() as session:
        q = (
            select(Channel.id, Channel.username, KeywordsCache.keywords_json)
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        res = await session.execute(q)
        rows = res.all()

    # Собираем только те каналы, у которых есть непустые ключи
    ids: List[int] = []
    texts: List[str] = []

    for cid, username, kw_json in rows:
        if not kw_json:
            continue

        try:
            parsed = json.loads(kw_json)
        except Exception:
            continue

        if not isinstance(parsed, list):
            continue

        tokens = [str(x).strip() for x in parsed if str(x).strip()]
        if not tokens:
            continue

        ids.append(cid)
        texts.append(" ".join(tokens))

    if target_channel_id not in ids:
        raise ValueError("У этого канала ещё нет ключевых слов. Сначала запусти LLM-анализ.")

    if len(ids) < 2:
        raise ValueError("Недостаточно каналов с ключевыми словами для поиска похожих.")

    # --- TF-IDF только по нормальным текстам ---
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer()
    tfidf = vec.fit_transform(texts)
    sim_matrix = cosine_similarity(tfidf)

    idx = ids.index(target_channel_id)
    sims = sim_matrix[idx]

    pairs = sorted(
        [
            (cid, float(score))
            for cid, score in zip(ids, sims)
            if cid != target_channel_id
        ],
        key=lambda x: x[1],
        reverse=True,
    )[:top_n]

    async with async_session_maker() as session:
        payload = json.dumps(
            [{"channel_id": cid, "score": score} for cid, score in pairs]
        )

        row = AnalyticsResults(
            channel_id=target_channel_id,
            similar_channels_json=payload,
        )
        session.add(row)
        await session.commit()
