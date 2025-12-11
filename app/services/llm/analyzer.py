import json
import re
from datetime import datetime

from pymorphy2 import MorphAnalyzer
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
from app.services.llm.client import ask_llm
from app.services.llm.prompt import build_analysis_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)

morph = MorphAnalyzer()


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"http[s]?://\S+", "", text)
    text = re.sub(r"t\.me/\S+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    return text.strip()


def extract_keywords_from_text(text: str, limit=20) -> list:
    tokens = re.findall(r"[A-Za-zА-Яа-яёЁ0-9]{4,}", text.lower())
    tokens = [t for t in tokens if len(t) >= 4]
    return list(dict.fromkeys(tokens))[:limit]


def normalize_russian_keywords(words: list) -> list:
    normalized = []
    for w in words:
        w = w.lower().strip()

        if len(w) < 3:
            continue
        if re.fullmatch(r"\d+", w):
            continue

        try:
            norm = morph.parse(w)[0].normal_form
        except Exception:
            norm = w

        if norm not in normalized:
            normalized.append(norm)

    return normalized[:20]


async def analyze_channel(channel: dict, posts: list):
    logger.info("LLM analysis started: posts=%s", len(posts))

    for p in posts[:5]:
        logger.debug("POST TEXT SAMPLE: %r", p.get("text"))

    description = clean_text(channel.get("description", "") or "")

    fragments = []
    for p in posts[:20]:
        text = clean_text(p.get("text", ""))
        if text:
            fragments.append(text[:500])

    if not fragments and not description:
        return {
            "audience": "Контента нет — анализ невозможен.",
            "keywords": [],
            "tone": ""
        }

    posts_text = "\n\n".join(fragments)
    prompt = build_analysis_prompt(description, posts_text)

    raw = await ask_llm(prompt, max_tokens=600)

    try:
        res = json.loads(raw)

        kws = res.get("keywords") or []
        kws = normalize_russian_keywords(kws)
        res["keywords"] = kws

        return res

    except Exception as e:
        logger.error("LLM response parse error: %s", e)

        fallback_source = (description + " " + posts_text).strip()
        kws = extract_keywords_from_text(fallback_source)
        kws = normalize_russian_keywords(kws)

        return {
            "audience": "Не удалось распарсить JSON",
            "tone": "",
            "keywords": kws
        }


async def save_analysis(channel_id: int, result: dict):
    """
    Сохраняет результат LLM в channels/keywords_cache через SQLAlchemy.
    """
    keywords = result.get("keywords") or []
    audience = result.get("audience", "")

    async with async_session_maker() as session:
        channel = await session.get(Channel, channel_id)
        if channel:
            channel.keywords = keywords
            channel.last_update = datetime.utcnow()

        kc = await session.get(KeywordsCache, channel_id)
        if not kc:
            kc = KeywordsCache(
                channel_id=channel_id,
                audience=audience,
                keywords_json=json.dumps(keywords),
                created_at=datetime.utcnow(),
            )
            session.add(kc)
        else:
            kc.audience = audience
            kc.keywords_json = json.dumps(keywords)
            kc.created_at = datetime.utcnow()

        await session.commit()

    logger.info("SAVE_ANALYSIS OK → channel_id=%s keywords=%s", channel_id, keywords)
