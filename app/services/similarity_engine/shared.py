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


def is_noise_channel(username: str | None, title: str | None, tokens: List[str]) -> bool:
    name = f"{username or ''} {title or ''}".lower()

    noise_markers = [
        "sticker", "stickers", "стикер", "стикеры",
        "emoji", "эмодзи",
        "gif", "гиф",
        "memes", "мемы", "meme",
        "аниме", "anime",
    ]
    if any(m in name for m in noise_markers):
        return True

    noise_keys = {
        "стикер", "стикеры", "emoji", "эмодзи",
        "gif", "гиф", "мем", "мемы",
        "стикерпак", "stickers", "смайл", "смайлики",
    }

    if tokens:
        noise_count = sum(1 for t in tokens if t in noise_keys)
        if noise_count / max(1, len(tokens)) >= 0.5:
            return True

    if len(tokens) < 3:
        return True

    return False


async def load_keywords_corpus() -> Tuple[Dict[int, List[str]], Dict[int, Dict[str, str | None]]]:
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

    tokens_by_channel: Dict[int, List[str]] = {}
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

        tokens_by_channel[cid] = tokens
        meta_by_channel[cid] = {"username": username, "title": title}

    return tokens_by_channel, meta_by_channel
