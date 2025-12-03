from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.db.session import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults
from sqlalchemy import select

import json
from datetime import datetime


class SimilarityEngine:

    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    async def load_data(self):
        async with async_session_maker() as session:
            q = (
                select(Channel, KeywordsCache)
                .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
            )
            rows = (await session.execute(q)).all()

        channels = []
        docs = []

        for ch, kw in rows:
            text = (ch.description or "").strip()
            try:
                keywords = json.loads(kw.keywords_json) if kw.keywords_json else []
            except:
                keywords = []

            if not text and not keywords:
                continue

            doc = text + " " + " ".join(keywords)
            channels.append(ch)
            docs.append(doc)

        return channels, docs

    async def calculate_similarity(self):
        channels, docs = await self.load_data()

        vectorizer = TfidfVectorizer(max_features=5000)
        matrix = vectorizer.fit_transform(docs)

        sim = cosine_similarity(matrix)

        results = []

        for idx, ch in enumerate(channels):
            scores = sim[idx]
            top_idx = scores.argsort()[::-1][1:self.top_n + 1]

            similar_list = [
                {
                    "channel_id": channels[j].id,
                    "score": float(scores[j])
                }
                for j in top_idx
            ]

            results.append((ch.id, similar_list))

        await self.save_results(results)

    async def save_results(self, data):
        async with async_session_maker() as session:
            for ch_id, similar in data:
                entry = AnalyticsResults(
                    channel_id=ch_id,
                    similar_channels_json=json.dumps(similar, ensure_ascii=False),
                    created_at=datetime.utcnow()
                )
                session.add(entry)

            await session.commit()
