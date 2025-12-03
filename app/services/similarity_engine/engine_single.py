import json
import re
import unicodedata
from typing import List
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults


def normalize_text(text: str) -> str:
    """
    Приводим unicode к NFC, выкидываем всё кроме букв и цифр,
    заменяем разделители на пробелы.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    # оставляем только буквы/цифры, остальное → пробел
    text = re.sub(r"[^0-9a-zA-Zа-яёА-ЯЁ]+", " ", text)
    return text.strip()


async def calculate_similarity_for_channel(target_channel_id: int, top_n: int = 10):
    """
    УЛЬТРА-СТАБИЛЬНАЯ версия TF-IDF похожих каналов.
    Работает даже на русских текстах, фразах и смешанных ключах.
    """

    # 1. Загружаем каналы, у которых есть keywords_cache
    async with async_session_maker() as session:
        q = (
            select(Channel.id, Channel.username, KeywordsCache.keywords_json)
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        rows = (await session.execute(q)).all()

    if not rows:
        raise ValueError("Нет каналов с keywords_cache.")

    ids: List[int] = []
    docs: List[str] = []

    for cid, username, kw_json in rows:

        # JSON → список
        try:
            kws = json.loads(kw_json)
        except Exception:
            continue

        if not isinstance(kws, list) or not kws:
            continue

        # нормализация всех keywords
        tokens = []
        for kw in kws:
            norm = normalize_text(str(kw))
            if norm:
                tokens.extend(norm.split())

        if not tokens:
            continue

        ids.append(cid)
        docs.append(" ".join(tokens))

    # 2. Проверяем, попал ли target в выборку
    if target_channel_id not in ids:
        raise ValueError("У канала есть keywords_cache, но он не прошёл фильтрацию под TF-IDF.")

    # 3. TF-IDF
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(docs)
    sims = cosine_similarity(X)

    idx = ids.index(target_channel_id)
    similarity_row = sims[idx]

    # 4. Топ каналов
    pairs = sorted(
        [(cid, float(score)) for cid, score in zip(ids, similarity_row) if cid != target_channel_id],
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    # 5. Записываем результат
    async with async_session_maker() as session:
        payload = json.dumps([
            {"channel_id": cid, "score": score} for cid, score in pairs
        ])

        session.add(AnalyticsResults(
            channel_id=target_channel_id,
            similar_channels_json=payload
        ))
        await session.commit()

    return True
