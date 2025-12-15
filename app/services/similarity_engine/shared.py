# app/services/similarity_engine/shared.py
"""
Общие утилиты для similarity engine.

ВАЖНО: Импортер (excel_importer.py) уже фильтрует мусор!
Здесь минимальная логика - не дублируем фильтрацию.
"""

import json
import re
import unicodedata
from typing import Dict, List, Tuple, Set

from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache


def normalize_text(text: str) -> str:
    """Нормализация текста для токенизации."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = re.sub(r"[^0-9a-zA-Zа-яёА-ЯЁ]+", " ", text)
    return text.strip()


# Категории, которые НЕ участвуют в similarity (развлекательный контент)
EXCLUDED_CATEGORIES = {
    "блоги",
    "цитаты", 
    "картинки и фото",
    "юмор и развлечения",
    "для взрослых",
    "эзотерика",
    "даркнет",
    "шок-контент",
    "эротика",
    "инстаграм",
    "telegram",
    "другое",
}


def should_exclude_category(category: str | None) -> bool:
    """Проверяет, исключена ли категория из similarity."""
    if not category:
        return False
    return category.strip().lower() in EXCLUDED_CATEGORIES


async def load_keywords_corpus(
    filter_noise: bool = True
) -> Tuple[Dict[int, List[str]], Dict[int, Dict[str, str | None]]]:
    """
    Загружает корпус keywords для similarity.
    
    Args:
        filter_noise: Исключать "мусорные" категории (Блоги, Цитаты, etc)
    
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
                Channel.category,
                KeywordsCache.keywords_json,
            )
            .join(KeywordsCache, KeywordsCache.channel_id == Channel.id)
        )
        rows = (await session.execute(q)).all()

    tokens_by_channel: Dict[int, List[str]] = {}
    meta_by_channel: Dict[int, Dict[str, str | None]] = {}

    for cid, username, title, category, kw_json in rows:
        if not kw_json:
            continue

        try:
            keywords = json.loads(kw_json)
        except Exception:
            continue

        if not isinstance(keywords, list) or not keywords:
            continue

        # Фильтруем исключённые категории
        if filter_noise and should_exclude_category(category):
            continue

        # Нормализация токенов (минимальная, т.к. импортер уже очистил)
        tokens: List[str] = []
        for kw in keywords:
            t = str(kw).lower().strip()
            if len(t) >= 2:
                tokens.append(t)

        if not tokens:
            continue

        tokens_by_channel[cid] = tokens
        meta_by_channel[cid] = {
            "username": username,
            "title": title,
            "category": (category or "").strip().lower(),
        }

    return tokens_by_channel, meta_by_channel
