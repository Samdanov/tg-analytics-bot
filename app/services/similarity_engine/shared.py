import json
import re
import unicodedata
from typing import Dict, List, Tuple, Set

from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^0-9a-zA-Zа-яёА-ЯЁ]+", " ", text)
    return text.strip()


# Мусорные категории - не подходят для бизнес-подбора
NOISE_CATEGORIES = {
    "блоги", "блог",
    "цитаты", "цитата",
    "картинки и фото", "картинки",
    "юмор", "мемы",
    "для взрослых", "18+",
    "эзотерика", "астрология",
    "даркнет",
    "инстаграм", "instagram",
    "telegram",
    "другое",
}


def is_noise_channel(
    username: str | None, 
    title: str | None, 
    tokens: List[str], 
    category: str | None = None
) -> bool:
    """
    Проверяет, является ли канал "мусорным" (не подходит для similarity).
    
    Args:
        username: Username канала
        title: Название канала
        tokens: Нормализованные токены из keywords
        category: Категория канала (из БД, не из keywords!)
    """
    name = f"{username or ''} {title or ''}".lower()

    # Маркеры мусора в названии
    noise_markers = [
        "sticker", "stickers", "стикер", "стикеры",
        "emoji", "эмодзи",
        "gif", "гиф",
        "memes", "мемы", "meme",
        "аниме", "anime",
    ]
    if any(m in name for m in noise_markers):
        return True

    # Мусорные токены в keywords
    noise_keys = {
        "стикер", "стикеры", "emoji", "эмодзи",
        "gif", "гиф", "мем", "мемы",
        "стикерпак", "stickers", "смайл", "смайлики",
    }

    if tokens:
        noise_count = sum(1 for t in tokens if t in noise_keys)
        if noise_count / max(1, len(tokens)) >= 0.5:
            return True

    # Слишком мало токенов = ненадёжный контент
    if len(tokens) < 3:
        return True
    
    # Проверка на мусорную категорию (теперь используем реальную category из БД!)
    if category:
        category_lower = category.lower().strip()
        if category_lower in NOISE_CATEGORIES:
            return True

    return False


async def load_keywords_corpus(
    filter_noise: bool = True
) -> Tuple[Dict[int, List[str]], Dict[int, Dict[str, str | None]]]:
    """
    Загружает корпус keywords для similarity.
    
    Args:
        filter_noise: Фильтровать мусорные каналы (Блоги, Цитаты, etc)
    
    Returns:
        tokens_by_channel: {channel_id: [token1, token2, ...]}
        meta_by_channel: {channel_id: {"username": ..., "title": ..., "category": ...}}
    """
    async with async_session_maker() as session:
        q = (
            select(
                Channel.id,
                Channel.username,
                Channel.title,
                Channel.category,  # Добавляем category для фильтрации и бустинга
                KeywordsCache.keywords_json,
            )
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        rows = (await session.execute(q)).all()

    tokens_by_channel: Dict[int, List[str]] = {}
    meta_by_channel: Dict[int, Dict[str, str | None]] = {}
    filtered_noise = 0

    for cid, username, title, category, kw_json in rows:
        if not kw_json:
            continue

        try:
            kws = json.loads(kw_json)
        except Exception:
            continue

        if not isinstance(kws, list) or not kws:
            continue

        token_set: Set[str] = set()
        for kw in kws:
            norm = normalize_text(str(kw))
            if not norm:
                continue
            for t in norm.split():
                if len(t) < 3:
                    continue
                if re.fullmatch(r"\d+", t):
                    continue
                token_set.add(t)

        tokens = sorted(token_set)
        if not tokens:
            continue
        
        # Фильтруем мусорные каналы (Блоги, Цитаты, etc)
        # Используем category для фильтрации вместо первого keyword
        if filter_noise and is_noise_channel(username, title, tokens, category=category):
            filtered_noise += 1
            continue

        tokens_by_channel[cid] = tokens
        meta_by_channel[cid] = {"username": username, "title": title, "category": category}

    return tokens_by_channel, meta_by_channel
