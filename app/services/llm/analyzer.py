import json
import re

from pymorphy2 import MorphAnalyzer
from app.db.repo import get_pool
from app.services.llm.client import ask_llm
from app.services.llm.prompt import build_analysis_prompt

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
        except:
            norm = w

        if norm not in normalized:
            normalized.append(norm)

    return normalized[:20]


async def analyze_channel(channel: dict, posts: list):
    print("=== LLM ANALYSIS START ===")
    print("POST COUNT:", len(posts))

    for p in posts[:5]:
        print("POST TEXT SAMPLE:", repr(p.get("text")))

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
        print("LLM ERROR:", e)

        fallback_source = (description + " " + posts_text).strip()
        kws = extract_keywords_from_text(fallback_source)
        kws = normalize_russian_keywords(kws)

        return {
            "audience": "Не удалось распарсить JSON",
            "tone": "",
            "keywords": kws
        }


async def save_analysis(channel_id: int, result: dict):
    pool = await get_pool()

    await pool.execute(
        """UPDATE channels SET keywords = $2, last_update = NOW() WHERE id = $1""",
        channel_id,
        result.get("keywords") or []
    )

    await pool.execute(
        """
        INSERT INTO keywords_cache (channel_id, audience, keywords_json)
        VALUES ($1, $2, $3)
        ON CONFLICT(channel_id) DO UPDATE
        SET audience = EXCLUDED.audience,
            keywords_json = EXCLUDED.keywords_json,
            created_at = NOW()
        """,
        channel_id,
        result.get("audience", ""),
        json.dumps(result.get("keywords") or [])
    )

    print("SAVE_ANALYSIS OK → channel_id:", channel_id, "keywords:", result.get("keywords"))
