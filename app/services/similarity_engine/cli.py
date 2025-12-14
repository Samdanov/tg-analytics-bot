import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import delete

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging import setup_logging, get_logger
from app.services.usecases.similarity_service import recalc_all
from app.services.similarity_engine.shared import load_keywords_corpus, is_noise_channel
from app.db.database import async_session_maker
from app.db.models import AnalyticsResults

logger = get_logger(__name__)


def build_filtered_corpus(raw_tokens_by_channel, meta_by_channel, max_df_ratio: float, min_keywords_per_channel: int, ids_filter=None):
    filtered = {}
    for cid, tokens in raw_tokens_by_channel.items():
        if ids_filter is not None and cid not in ids_filter:
            continue
        meta = meta_by_channel.get(cid, {})
        if is_noise_channel(meta.get("username"), meta.get("title"), tokens):
            continue
        filtered[cid] = tokens

    if len(filtered) < 2:
        return [], []

    df = {}
    for tokens in filtered.values():
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1

    num_docs = len(filtered)
    frequent_tokens = {t for t, count in df.items() if count / num_docs > max_df_ratio}

    ids = []
    docs = []
    for cid, tokens in filtered.items():
        cleaned = [t for t in tokens if t not in frequent_tokens]
        if len(cleaned) < min_keywords_per_channel:
            continue
        ids.append(cid)
        docs.append(" ".join(cleaned))

    return ids, docs


async def recalc_seq(
    top_n: int = 10, 
    max_df_ratio: float = 0.3, 
    min_keywords_per_channel: int = 4, 
    commit_every: int = 200,
    start_idx: int = 0,
    end_idx: int = None
):
    """
    Последовательный пересчёт similarity.
    
    Args:
        top_n: Количество похожих каналов
        start_idx: Начальный индекс (для многопроцессорности)
        end_idx: Конечный индекс (для многопроцессорности)
    """
    raw_tokens_by_channel, meta_by_channel = await load_keywords_corpus()
    ids, docs = build_filtered_corpus(raw_tokens_by_channel, meta_by_channel, max_df_ratio, min_keywords_per_channel)

    total = len(ids)
    if total < 2:
        logger.warning("[SEQ] недостаточно каналов для similarity")
        return

    # Ограничиваем диапазон для многопроцессорности
    if end_idx is None or end_idx > total:
        end_idx = total
    if start_idx < 0:
        start_idx = 0
    if start_idx >= end_idx:
        logger.warning("[SEQ] неверный диапазон: start=%s, end=%s", start_idx, end_idx)
        return
    
    range_size = end_idx - start_idx
    logger.info("[SEQ] каналов всего: %s, обрабатываем: %s-%s (%s каналов)", 
                total, start_idx, end_idx, range_size)

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(docs)

    async with async_session_maker() as session:
        processed = 0
        for idx in range(start_idx, end_idx):
            cid = ids[idx]
            sims = cosine_similarity(X[idx], X).ravel()
            sims[idx] = 0.0

            pairs = [
                (other_id, float(score))
                for other_id, score in zip(ids, sims)
                if other_id != cid
            ]
            pairs.sort(key=lambda x: x[1], reverse=True)
            if top_n is not None and top_n > 0:
                pairs = pairs[:top_n]

            await session.execute(delete(AnalyticsResults).where(AnalyticsResults.channel_id == cid))
            payload = json.dumps([
                {"channel_id": ch, "score": sc} for ch, sc in pairs
            ])
            session.add(
                AnalyticsResults(
                    channel_id=cid,
                    similar_channels_json=payload,
                    created_at=datetime.utcnow(),
                )
            )

            processed += 1
            if processed % commit_every == 0:
                await session.commit()
                logger.info("[SEQ] processed %s/%s (global idx: %s)", processed, range_size, idx + 1)

        await session.commit()

    logger.info("[SEQ] готово, обработано: %s", processed)


async def recalc_chunked(top_n: int = 10, chunk_size: int = 2000, max_df_ratio: float = 0.3, min_keywords_per_channel: int = 4):
    raw_tokens_by_channel, meta_by_channel = await load_keywords_corpus()
    all_ids = list(raw_tokens_by_channel.keys())
    total = len(all_ids)
    if total < 2:
        logger.warning("[CHUNK] недостаточно каналов для similarity")
        return

    logger.info("[CHUNK] каналов для анализа: %s (chunk=%s)", total, chunk_size)

    async with async_session_maker() as session:
        for start in range(0, total, chunk_size):
            chunk_ids = set(all_ids[start:start + chunk_size])
            ids, docs = build_filtered_corpus(raw_tokens_by_channel, meta_by_channel, max_df_ratio, min_keywords_per_channel, ids_filter=chunk_ids)
            if len(ids) < 2:
                continue

            vectorizer = TfidfVectorizer()
            X = vectorizer.fit_transform(docs)

            for idx, cid in enumerate(ids):
                sims = cosine_similarity(X[idx], X).ravel()
                sims[idx] = 0.0

                pairs = [
                    (other_id, float(score))
                    for other_id, score in zip(ids, sims)
                    if other_id != cid
                ]
                pairs.sort(key=lambda x: x[1], reverse=True)
                if top_n is not None and top_n > 0:
                    pairs = pairs[:top_n]

                await session.execute(delete(AnalyticsResults).where(AnalyticsResults.channel_id == cid))
                payload = json.dumps([
                    {"channel_id": ch, "score": sc} for ch, sc in pairs
                ])
                session.add(
                    AnalyticsResults(
                        channel_id=cid,
                        similar_channels_json=payload,
                        created_at=datetime.utcnow(),
                    )
                )

            await session.commit()
            logger.info("[CHUNK] processed chunk %s-%s / %s", start + 1, min(total, start + chunk_size), total)

    logger.info("[CHUNK] готово")


async def main():
    setup_logging()

    mode = sys.argv[1] if len(sys.argv) >= 2 else "batch"
    top_n = int(sys.argv[2]) if len(sys.argv) >= 3 else 10

    if mode == "batch":
        await recalc_all(top_n=top_n)
    elif mode == "seq":
        # Поддержка многопроцессорности: seq top_n [start_idx] [end_idx]
        start_idx = int(sys.argv[3]) if len(sys.argv) >= 4 else 0
        end_idx = int(sys.argv[4]) if len(sys.argv) >= 5 else None
        await recalc_seq(top_n=top_n, start_idx=start_idx, end_idx=end_idx)
    elif mode == "chunk":
        chunk_size = int(sys.argv[3]) if len(sys.argv) >= 4 else 2000
        await recalc_chunked(top_n=top_n, chunk_size=chunk_size)
    else:
        print("""
Usage: python -m app.services.similarity_engine.cli [mode] [top_n] [options]

Modes:
  batch              - Полный пересчёт (требует много RAM)
  seq top_n [start] [end] - Последовательный пересчёт (поддержка многопроцессорности)
  chunk top_n [chunk_size] - Пересчёт по чанкам

Examples:
  # Полный пересчёт
  python -m app.services.similarity_engine.cli seq 500
  
  # Многопроцессорность (4 терминала):
  python -m app.services.similarity_engine.cli seq 500 0 50000
  python -m app.services.similarity_engine.cli seq 500 50000 100000
  python -m app.services.similarity_engine.cli seq 500 100000 150000
  python -m app.services.similarity_engine.cli seq 500 150000 210000
""")


if __name__ == "__main__":
    asyncio.run(main())
