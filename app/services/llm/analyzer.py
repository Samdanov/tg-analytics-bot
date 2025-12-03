import json

from app.db.repo import get_pool
from app.services.llm.client import ask_llm
from app.services.llm.prompt import build_analysis_prompt


async def analyze_channel(channel: dict, posts: list):
    """
    Принимает:
    - data из channels
    - posts из posts
    Возвращает словарь с аналитикой.
    """

    description = channel.get("description", "") or ""
    
    # Берём не больше 20 коротких постов, чтобы не жечь токены
    fragments = []
    for p in posts[:20]:
        text = p.get("text", "")
        if text:
            fragments.append(text[:500])  # обрезаем каждый до 500 символов

    posts_text = "\n\n".join(fragments)

    prompt = build_analysis_prompt(description, posts_text)

    raw = await ask_llm(prompt, max_tokens=600)

    try:
        return json.loads(raw)
    except:
        return {
            "audience": "Не удалось распарсить JSON",
            "tone": "",
            "keywords": []
        }


async def save_analysis(channel_id, result):
    pool = await get_pool()

    audience = result.get("audience", "")

    keywords = result.get("keywords")
    if not keywords:
        # fallback — чтобы SimilarityEngine не падал
        keywords = ["general", "telegram", "channel"]

    query = """
        INSERT INTO keywords_cache (channel_id, audience, keywords_json)
        VALUES ($1, $2, $3)
        ON CONFLICT(channel_id) DO UPDATE
        SET audience = EXCLUDED.audience,
            keywords_json = EXCLUDED.keywords_json;
    """

    await pool.execute(
        query,
        channel_id,
        audience,
        json.dumps(keywords),
    )
