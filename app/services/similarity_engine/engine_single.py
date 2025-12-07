# app/services/similarity_engine/engine_single.py

import json
import re
import unicodedata
from typing import List

from sqlalchemy import select, delete
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults


def normalize_text(text: str) -> str:
    """
    Нормализуем текст:
    - приводим к NFC (unicode)
    - в нижний регистр
    - оставляем только буквы и цифры, остальное → пробел
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^0-9a-zA-Zа-яёА-ЯЁ]+", " ", text)
    return text.strip()


async def calculate_similarity_for_channel(target_channel_id: int, top_n: int = 10) -> bool:
    """
    Считает похожие каналы для ОДНОГО channel_id на основе keywords_cache.

    ВАЖНО:
    - НИКОГДА не выбрасывает исключение из-за TF-IDF.
    - В худшем случае пишет в analytics_results пустой список похожих каналов.
    - Работает на русских/английских ключах, даже если это фразы.
    """
    print("ENGINE_SINGLE >>> RUN target =", target_channel_id)

    # 1. Забираем все каналы, у которых есть keywords_cache
    async with async_session_maker() as session:
        q = (
            select(
                Channel.id,
                Channel.username,
                KeywordsCache.keywords_json,
            )
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        rows = (await session.execute(q)).all()

    if not rows:
        # Вообще нет каналов с кэшем — это реальная ошибка конфигурации
        raise ValueError("Нет ни одного канала с keywords_cache.")

    ids: List[int] = []
    docs: List[str] = []

    for cid, username, kw_json in rows:
        if not kw_json:
            continue

        try:
            kws = json.loads(kw_json)
        except Exception:
            continue

        if not isinstance(kws, list) or not kws:
            continue

        # Нормализуем ключи в список токенов
        tokens: List[str] = []
        for kw in kws:
            norm = normalize_text(str(kw))
            if not norm:
                continue
            tokens.extend(norm.split())

        # Если после нормализации вообще нет токенов — пропускаем канал
        if not tokens:
            # Но если это целевой канал — мы просто не сможем по нему считать,
            # ниже отдадим пустой результат, без ошибки для пользователя.
            continue

        ids.append(cid)
        docs.append(" ".join(tokens))

    # Если целевой канал вообще не попал в выборку (нет токенов, пустой текст и т.п.)
    if target_channel_id not in ids:
        # Записываем пустой analytics_results и считаем, что всё ОК, просто похожих нет.
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            empty_payload = json.dumps([])
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=empty_payload,
                )
            )
            await session.commit()
        return False

    # Если в выборке вообще только один канал (наш) — считаем, что похожих нет.
    if len(ids) == 1:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            empty_payload = json.dumps([])
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=empty_payload,
                )
            )
            await session.commit()
        return False

    # 3. Строим TF-IDF только по тем документам, которые прошли фильтрацию
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(docs)
    sim_matrix = cosine_similarity(X)

    target_index = ids.index(target_channel_id)
    sim_row = sim_matrix[target_index]

    # 4. Формируем список (channel_id, score), исключая сам канал
    pairs = [
        (cid, float(score))
        for cid, score in zip(ids, sim_row)
        if cid != target_channel_id
    ]
    pairs.sort(key=lambda x: x[1], reverse=True)

    if top_n is not None and top_n > 0:
        pairs = pairs[:top_n]

    # 5. Сохраняем результат в analytics_results (перезаписываем старый)
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

    return True
