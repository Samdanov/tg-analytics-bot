import json
from typing import List, Dict, Set
from math import log, sqrt

from sqlalchemy import delete

from app.db.database import async_session_maker
from app.db.models import AnalyticsResults
from app.core.logging import get_logger
from app.services.similarity_engine.shared import (
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
    Лёгкий по памяти расчёт похожих каналов для одного channel_id.
    Вместо большой TF-IDF матрицы считаем IDF и пересечение токенов.
    """
    logger.info("ENGINE_SINGLE v2.2 run target=%s", target_channel_id)

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
        for t in set(tokens):
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

    cleaned_by_channel: Dict[int, List[str]] = {}
    for cid, tokens in filtered_tokens_by_channel.items():
        cleaned = [t for t in tokens if t not in frequent_tokens]
        if len(cleaned) < min_keywords_per_channel:
            continue
        cleaned_by_channel[cid] = cleaned

    if target_channel_id not in cleaned_by_channel or len(cleaned_by_channel) < 2:
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

    # IDF weights
    idf = {t: log(num_docs / (1 + df_val)) for t, df_val in df.items() if t not in frequent_tokens}

    target_tokens = cleaned_by_channel[target_channel_id]
    target_set = set(target_tokens)
    target_len = len(target_tokens)

    pairs = []
    for cid, tokens in cleaned_by_channel.items():
        if cid == target_channel_id:
            continue
        common = target_set.intersection(tokens)
        if not common:
            continue
        score = sum(idf.get(t, 0.0) for t in common)
        denom = sqrt(target_len * len(tokens)) or 1.0
        score /= denom
        pairs.append((cid, float(score)))

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
