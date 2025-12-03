import json
import re

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
        res = json.loads(raw)
        # fallback — если LLM дал пустой список
        if not res.get("keywords"):
            description = channel.get("description", "") or ""
            tokens = re.findall(r"[A-Za-zА-Яа-яёЁ0-9]{4,}", description.lower())
            res["keywords"] = list(set(tokens[:15])) or ["ai", "tech", "news"]

        return res

    except:
        return {
            "audience": "Не удалось распарсить JSON",
            "tone": "",
            "keywords": []
        }


async def save_analysis(channel_id: int, result: dict):
    pool = await get_pool()

    keywords = result.get("keywords") or []
    audience = result.get("audience", "")

    await pool.execute(
        """
        UPDATE channels
        SET keywords = $2, last_update = NOW()
        WHERE id = $1
        """,
        channel_id,
        keywords
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
        audience,
        json.dumps(keywords)
    )

    print("SAVE_ANALYSIS OK → channel_id:", channel_id, "keywords:", keywords)
