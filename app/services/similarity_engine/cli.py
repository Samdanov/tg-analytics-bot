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


async def build_corpus(max_df_ratio: float = 0.3, min_keywords_per_channel: int = 4):
    raw_tokens_by_channel, meta_by_channel = await load_keywords_corpus()

    filtered = {}
    for cid, tokens in raw_tokens_by_channel.items():
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


async def recalc_seq(top_n: int = 10, max_df_ratio: float = 0.3, min_keywords_per_channel: int = 4, commit_every: int = 200):
    ids, docs = await build_corpus(max_df_ratio=max_df_ratio, min_keywords_per_channel=min_keywords_per_channel)

    total = len(ids)
    if total < 2:
        logger.warning("[SEQ] недостаточно каналов для similarity")
        return

    logger.info("[SEQ] каналов для анализа: %s", total)

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(docs)

    async with async_session_maker() as session:
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

            if (idx + 1) % commit_every == 0:
                await session.commit()
                logger.info("[SEQ] processed %s/%s", idx + 1, total)

        await session.commit()

    logger.info("[SEQ] готово")


async def main():
    setup_logging()

    mode = sys.argv[1] if len(sys.argv) >= 2 else "batch"
    top_n = int(sys.argv[2]) if len(sys.argv) >= 3 else 10

    if mode == "batch":
        await recalc_all(top_n=top_n)
    elif mode == "seq":
        await recalc_seq(top_n=top_n)
    else:
        print("Usage: python -m app.services.similarity_engine.cli [batch|seq] [top_n]")


if __name__ == "__main__":
    asyncio.run(main())
