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
        w = w.strip()

        if len(w) < 3:
            continue
        if re.fullmatch(r"\d+", w):
            continue

        # Проверяем, содержит ли латиницу или цифры (технические термины, бренды)
        has_latin = bool(re.search(r"[a-zA-Z]", w))
        has_mixed = bool(re.search(r"[a-zA-Z]", w)) and bool(re.search(r"[а-яёА-ЯЁ]", w))
        
        # Не нормализуем:
        # - латинские слова и бренды (Discord, Windows, SSD)
        # - смешанные слова (Wi-Fi, iPhone)
        # - слова с цифрами (Windows 11, Python3)
        # - аббревиатуры в верхнем регистре (AI, ML, SSD)
        if has_latin or has_mixed or re.search(r"\d", w) or w.isupper():
            norm = w.lower()
        else:
            # Только чисто русские слова нормализуем через pymorphy2
            try:
                norm = morph.parse(w.lower())[0].normal_form
            except Exception:
                norm = w.lower()

        if norm not in normalized:
            normalized.append(norm)

    return normalized[:20]


def try_parse_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        pass

    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass

    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    return None


async def analyze_channel(channel: dict, posts: list, llm_retries: int = 2):
    logger.info("LLM analysis started: posts=%s", len(posts))

    for p in posts[:5]:
        logger.debug("POST TEXT SAMPLE: %r", p.get("text"))

    title = clean_text(channel.get("title", "") or "")
    description = clean_text(channel.get("description", "") or channel.get("about", "") or "")

    all_posts_text = []
    for p in posts:
        text = clean_text(p.get("text", ""))
        if text:
            all_posts_text.append(text[:500])

    fragments = all_posts_text[:20]

    if not fragments and not description:
        kws = extract_keywords_from_text(title, limit=20)
        kws = normalize_russian_keywords(kws)
        
        # Для ID-based каналов используем ID вместо username
        fallback_identifier = channel.get("username") or f"id_{channel.get('id', 'unknown')}"
        return {
            "audience": "Контента нет — анализ невозможен.",
            "keywords": kws if kws else [fallback_identifier],
            "tone": ""
        }

    posts_text = "\n\n".join(fragments)
    prompt = build_analysis_prompt(description, posts_text)

    last_error = None
    for attempt in range(llm_retries + 1):
        try:
            raw = await ask_llm(prompt, max_tokens=600)
            res = try_parse_json(raw)

            if res and isinstance(res.get("keywords"), list):
                kws = res.get("keywords") or []
                kws = normalize_russian_keywords(kws)
                res["keywords"] = kws
                return res
            else:
                last_error = f"Invalid JSON structure: {raw[:200]}"
                logger.warning("LLM attempt %s: %s", attempt + 1, last_error)

        except Exception as e:
            last_error = str(e)
            logger.warning("LLM attempt %s error: %s", attempt + 1, e)

    logger.error("LLM failed after %s attempts: %s", llm_retries + 1, last_error)
    fallback_source = " ".join([title, description] + all_posts_text)
    kws = extract_keywords_from_text(fallback_source, limit=30)
    kws = normalize_russian_keywords(kws)

    return {
        "audience": "Не удалось получить анализ от LLM",
        "tone": "",
        "keywords": kws
    }


async def analyze_text_content(text: str, title: str = "", description: str = "", llm_retries: int = 2) -> dict:
    """
    Анализирует текстовый контент (например, с сайта) через LLM.
    Аналогично analyze_channel, но работает с готовым текстом.
    
    Args:
        text: Текст для анализа
        title: Заголовок (опционально)
        description: Описание (опционально)
        llm_retries: Количество попыток запроса к LLM
    
    Returns:
        Словарь с результатами анализа: {audience, keywords, tone}
    """
    logger.info("LLM analysis started for text content: length=%s", len(text))
    
    title_clean = clean_text(title or "")
    description_clean = clean_text(description or "")
    
    # Берем первые 5000 символов текста для анализа
    text_clean = clean_text(text)[:5000]
    
    if not text_clean and not description_clean:
        kws = extract_keywords_from_text(title_clean, limit=20)
        kws = normalize_russian_keywords(kws)
        return {
            "audience": "Контента нет — анализ невозможен.",
            "keywords": kws if kws else [],
            "tone": ""
        }
    
    # Формируем промпт для анализа
    content_text = text_clean[:3000]  # Ограничиваем длину для LLM
    prompt = build_analysis_prompt(description_clean, content_text)
    
    last_error = None
    for attempt in range(llm_retries + 1):
        try:
            raw = await ask_llm(prompt, max_tokens=600)
            res = try_parse_json(raw)
            
            if res and isinstance(res.get("keywords"), list):
                kws = res.get("keywords") or []
                kws = normalize_russian_keywords(kws)
                res["keywords"] = kws
                return res
            else:
                last_error = f"Invalid JSON structure: {raw[:200]}"
                logger.warning("LLM attempt %s: %s", attempt + 1, last_error)
        
        except Exception as e:
            last_error = str(e)
            logger.warning("LLM attempt %s error: %s", attempt + 1, e)
    
    logger.error("LLM failed after %s attempts: %s", llm_retries + 1, last_error)
    fallback_source = " ".join([title_clean, description_clean, text_clean])
    kws = extract_keywords_from_text(fallback_source, limit=30)
    kws = normalize_russian_keywords(kws)
    
    return {
        "audience": "Не удалось получить анализ от LLM",
        "tone": "",
        "keywords": kws
    }


async def save_analysis(channel_id: int, result: dict):
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
