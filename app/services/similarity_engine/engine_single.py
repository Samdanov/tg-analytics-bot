import json
from typing import List, Dict, Set

from sqlalchemy import delete

from app.db.database import async_session_maker
from app.db.models import AnalyticsResults
from app.core.logging import get_logger
from app.services.similarity_engine.shared import (
    normalize_text,
    is_noise_channel,
    load_keywords_corpus,
)

logger = get_logger(__name__)


async def calculate_similarity_for_channel(
    target_channel_id: int,
    top_n: int = 10,
    max_df_ratio: float = 0.3,
    min_keywords_per_channel: int = 4,
) -> bool:
    """
    Считает похожие каналы для ОДНОГО channel_id на основе keywords_cache.
    Общая логика нормализации/фильтрации вынесена в shared.
    """
    logger.info("ENGINE_SINGLE v2.1 run target=%s", target_channel_id)

    raw_tokens_by_channel, meta_by_channel = await load_keywords_corpus()

    if target_channel_id not in raw_tokens_by_channel:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    filtered_tokens_by_channel: Dict[int, List[str]] = {}
    for cid, tokens in raw_tokens_by_channel.items():
        meta = meta_by_channel.get(cid, {})
        if cid != target_channel_id and is_noise_channel(meta.get("username"), meta.get("title"), tokens):
            continue
        filtered_tokens_by_channel[cid] = tokens

    if target_channel_id not in filtered_tokens_by_channel:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    df: Dict[str, int] = {}
    for tokens in filtered_tokens_by_channel.values():
        unique = set(tokens)
        for t in unique:
            df[t] = df.get(t, 0) + 1

    num_docs = len(filtered_tokens_by_channel)
    if num_docs < 2:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    frequent_tokens: Set[str] = set()
    for t, count in df.items():
        if count / num_docs > max_df_ratio:
            frequent_tokens.add(t)

    ids: List[int] = []
    docs: List[str] = []

    for cid, tokens in filtered_tokens_by_channel.items():
        cleaned = [t for t in tokens if t not in frequent_tokens]
        if len(cleaned) < min_keywords_per_channel:
            continue
        ids.append(cid)
        docs.append(" ".join(cleaned))

    if target_channel_id not in ids or len(ids) < 2:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(docs)
    sim_matrix = cosine_similarity(X)

    target_index = ids.index(target_channel_id)
    sim_row = sim_matrix[target_index]

    pairs = [
        (cid, float(score))
        for cid, score in zip(ids, sim_row)
        if cid != target_channel_id
    ]
    pairs.sort(key=lambda x: x[1], reverse=True)

    if top_n is not None and top_n > 0:
        pairs = pairs[:top_n]

    async with async_session_maker() as session:
        await session.execute(
            delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
        )
        payload = json.dumps(
            [{"channel_id": cid, "score": score} for cid, score in pairs]
        )
        session.add(
            AnalyticsResults(
                channel_id=target_channel_id,
                similar_channels_json=payload,
            )
        )
        await session.commit()

    logger.info("ENGINE_SINGLE finished target=%s results=%s", target_channel_id, len(pairs))
    return True
