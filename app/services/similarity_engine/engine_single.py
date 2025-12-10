# app/services/similarity_engine/engine_single.py

import json
import re
import unicodedata
from typing import List, Dict, Set

from sqlalchemy import select, delete

from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache, AnalyticsResults


def normalize_text(text: str) -> str:
    """
    Нормализуем текст:
    - Unicode NFC
    - нижний регистр
    - только буквы и цифры, остальное → пробел
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^0-9a-zA-Zа-яёА-ЯЁ]+", " ", text)
    return text.strip()


def is_noise_channel(username: str | None, title: str | None, tokens: List[str]) -> bool:
    """
    Выявляем шумовые/мусорные каналы:
    - стикеры, эмодзи, гифки, мемо-свалки и т.п.
    - очень мало осмысленных токенов
    """
    name = f"{username or ''} {title or ''}".lower()

    # По имени канала
    noise_markers = [
        "sticker", "stickers", "стикер", "стикеры",
        "emoji", "эмодзи",
        "gif", "гиф",
        "memes", "мемы", "meme",
        "аниме", "anime",
    ]
    if any(m in name for m in noise_markers):
        return True

    # По ключам
    noise_keys = {
        "стикер", "стикеры", "emoji", "эмодзи",
        "gif", "гиф", "мем", "мемы",
        "стикерпак", "stickers", "смайл", "смайлики",
    }

    if tokens:
        noise_count = sum(1 for t in tokens if t in noise_keys)
        if noise_count / max(1, len(tokens)) >= 0.5:
            return True

    # Совсем мало токенов → слабый сигнал, считаем шумом
    if len(tokens) < 3:
        return True

    return False


async def calculate_similarity_for_channel(
    target_channel_id: int,
    top_n: int = 10,
    max_df_ratio: float = 0.3,   # отсечение слишком частых слов
    min_keywords_per_channel: int = 4,  # минимум токенов после фильтрации
) -> bool:
    """
    Считает похожие каналы для ОДНОГО channel_id на основе keywords_cache.

    ENGINE v2.0:
    - используем только keywords_cache
    - режем слишком частые токены (IDF-cutoff)
    - выкидываем мусорные каналы (стикеры/эмодзи/гифки/мемосвалки)
    - игнорируем каналы с маленьким числом ключей
    - никогда не кидаем исключения «в лицо пользователю» — максимум пишем пустой результат
    """
    print("ENGINE_SINGLE v2.0 >>> RUN target =", target_channel_id)

    async with async_session_maker() as session:
        q = (
            select(
                Channel.id,
                Channel.username,
                Channel.title,
                KeywordsCache.keywords_json,
            )
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        rows = (await session.execute(q)).all()

    if not rows:
        raise ValueError("Нет ни одного канала с keywords_cache.")

    # ---- 1. Собираем сырые токены по каналам ----
    raw_tokens_by_channel: Dict[int, List[str]] = {}
    meta_by_channel: Dict[int, Dict[str, str | None]] = {}

    for cid, username, title, kw_json in rows:
        if not kw_json:
            continue

        try:
            kws = json.loads(kw_json)
        except Exception:
            continue

        if not isinstance(kws, list) or not kws:
            continue

        # нормализуем ключевые слова → набор токенов
        token_set: Set[str] = set()
        for kw in kws:
            norm = normalize_text(str(kw))
            if not norm:
                continue
            for t in norm.split():
                # отсечём совсем короткие и числовые
                if len(t) < 3:
                    continue
                if re.fullmatch(r"\d+", t):
                    continue
                token_set.add(t)

        tokens = sorted(token_set)
        if not tokens:
            continue

        raw_tokens_by_channel[cid] = tokens
        meta_by_channel[cid] = {"username": username, "title": title}

    if target_channel_id not in raw_tokens_by_channel:
        # Для целевого канала нет токенов → просто сохраняем пустой результат
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

    # ---- 2. Отбрасываем шумовые каналы (стикеры/мемы и т.п.) ----
    filtered_tokens_by_channel: Dict[int, List[str]] = {}
    for cid, tokens in raw_tokens_by_channel.items():
        meta = meta_by_channel.get(cid, {})
        if cid != target_channel_id and is_noise_channel(meta.get("username"), meta.get("title"), tokens):
            continue
        filtered_tokens_by_channel[cid] = tokens

    if target_channel_id not in filtered_tokens_by_channel:
        # наш канал сам оказался шумовым → нет смысла считать similarity
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

    # ---- 3. Считаем document frequency (DF) по токенам ----
    df: Dict[str, int] = {}
    for tokens in filtered_tokens_by_channel.values():
        unique = set(tokens)
        for t in unique:
            df[t] = df.get(t, 0) + 1

    num_docs = len(filtered_tokens_by_channel)
    if num_docs < 2:
        # слишком мало каналов для сравнения
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

    # ---- 4. Отсекаем слишком частые токены (IDF-cutoff) ----
    # Токен, встречающийся > max_df_ratio * каналов, считаем шумом ("новости", "экономика", "Россия", ...).
    frequent_tokens: Set[str] = set()
    for t, count in df.items():
        if count / num_docs > max_df_ratio:
            frequent_tokens.add(t)

    # Формируем окончательный корпус: выкидываем мусорные токены
    ids: List[int] = []
    docs: List[str] = []

    for cid, tokens in filtered_tokens_by_channel.items():
        cleaned = [t for t in tokens if t not in frequent_tokens]
        if len(cleaned) < min_keywords_per_channel:
            # канал слишком "пустой" после фильтров
            continue
        ids.append(cid)
        docs.append(" ".join(cleaned))

    # Если после всех фильтров наш канал выпал → нет похожих
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

    # ---- 5. Строим TF-IDF и косинусное сходство ----
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

    # ---- 6. Сохраняем результат ----
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
