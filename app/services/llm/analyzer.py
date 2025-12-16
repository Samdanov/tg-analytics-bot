import json
import re
from datetime import datetime

from pymorphy2 import MorphAnalyzer
from app.db.database import async_session_maker
from app.db.models import Channel, KeywordsCache
from app.services.llm.client import ask_llm
from app.services.llm.prompt import build_analysis_prompt, VALID_CATEGORIES
from app.core.logging import get_logger

logger = get_logger(__name__)

morph = MorphAnalyzer()


def normalize_category(raw_category: str) -> str:
    """
    Нормализует category к одной из 48 валидных тем.
    
    ВАЖНО: Всегда возвращает валидную категорию из списка.
    Если не удаётся определить → "другое"
    """
    if not raw_category:
        return "другое"
    
    cleaned = raw_category.strip().lower()
    
    if not cleaned or cleaned in ("nan", "none", "null", ""):
        return "другое"
    
    # Прямое совпадение (основной случай)
    if cleaned in VALID_CATEGORIES:
        return cleaned
    
    # Маппинг частых опечаток/вариаций LLM
    aliases = {
        "it": "технологии",
        "tech": "технологии",
        "программирование": "технологии",
        "разработка": "технологии",
        "финансы": "экономика",
        "инвестиции": "экономика",
        "маркетинг": "маркетинг, pr, реклама",
        "реклама": "маркетинг, pr, реклама",
        "pr": "маркетинг, pr, реклама",
        "smm": "маркетинг, pr, реклама",
        "крипта": "криптовалюты",
        "crypto": "криптовалюты",
        "bitcoin": "криптовалюты",
        "авто": "транспорт",
        "автомобили": "транспорт",
        "юриспруденция": "право",
        "закон": "право",
        "здоровье": "здоровье и фитнес",
        "фитнес": "здоровье и фитнес",
        "спортзал": "здоровье и фитнес",
        "кино": "видео и фильмы",
        "фильмы": "видео и фильмы",
        "сериалы": "видео и фильмы",
        "косметика": "мода и красота",
        "красота": "мода и красота",
        "мода": "мода и красота",
        "еда": "еда и кулинария",
        "кулинария": "еда и кулинария",
        "рецепты": "еда и кулинария",
        "дети": "семья и дети",
        "родители": "семья и дети",
        "новости": "новости и сми",
        "сми": "новости и сми",
        "юмор": "юмор и развлечения",
        "мемы": "юмор и развлечения",
        "развлечения": "юмор и развлечения",
        "ставки": "букмекерство",
        "беттинг": "букмекерство",
        "gaming": "игры",
        "гейминг": "игры",
        "travel": "путешествия",
        "туризм": "путешествия",
    }
    
    if cleaned in aliases:
        return aliases[cleaned]
    
    # Поиск по вхождению (менее строгий)
    for valid in VALID_CATEGORIES:
        if cleaned in valid or valid in cleaned:
            return valid
    
    # Ничего не подошло → "другое"
    return "другое"


def tokenize_keywords(keywords: list) -> list:
    """
    Разбивает словосочетания на отдельные токены.
    
    "machine learning" → ["machine", "learning"]
    "контент-маркетинг" → ["контент", "маркетинг"]
    """
    tokens = []
    for kw in keywords:
        if not kw:
            continue
        
        kw_str = str(kw).strip()
        
        # Разбиваем по пробелам и дефисам
        parts = re.split(r'[\s\-_]+', kw_str)
        
        for part in parts:
            part = part.strip()
            if len(part) >= 2:
                tokens.append(part)
    
    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique = []
    for t in tokens:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique.append(t)
    
    return unique


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
        
        return {
            "category": "другое",  # Нет контента для определения темы
            "audience": "Контента нет — анализ невозможен.",
            "keywords": kws if kws else [],
            "tone": ""
        }

    posts_text = "\n\n".join(fragments)
    prompt = build_analysis_prompt(description, posts_text)

    last_error = None
    for attempt in range(llm_retries + 1):
        try:
            raw = await ask_llm(prompt, max_tokens=800)
            res = try_parse_json(raw)

            if res and isinstance(res.get("keywords"), list):
                # Обрабатываем keywords: токенизация + нормализация
                kws = res.get("keywords") or []
                kws = tokenize_keywords(kws)  # Разбиваем словосочетания
                kws = normalize_russian_keywords(kws)
                res["keywords"] = kws
                
                # Обрабатываем category
                raw_category = res.get("category", "")
                res["category"] = normalize_category(raw_category)
                
                logger.info("LLM analysis: category='%s', keywords=%d", 
                           res["category"], len(res["keywords"]))
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
        "category": "другое",  # LLM не смог — назначаем "другое"
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
            "category": "другое",  # Нет контента для определения темы
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
            raw = await ask_llm(prompt, max_tokens=800)
            res = try_parse_json(raw)
            
            if res and isinstance(res.get("keywords"), list):
                kws = res.get("keywords") or []
                kws = tokenize_keywords(kws)
                kws = normalize_russian_keywords(kws)
                res["keywords"] = kws
                
                raw_category = res.get("category", "")
                res["category"] = normalize_category(raw_category)
                
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
        "category": "другое",  # LLM не смог — назначаем "другое"
        "audience": "Не удалось получить анализ от LLM",
        "tone": "",
        "keywords": kws
    }


async def save_analysis(channel_id: int, result: dict):
    """
    Сохраняет результаты LLM-анализа.
    
    Сохраняет:
    - category → channels.category (PRIMARY TOPIC)
    - keywords → keywords_cache.keywords_json (SECONDARY)
    - audience, tone → keywords_cache
    """
    keywords = result.get("keywords") or []
    audience = result.get("audience", "")
    tone = result.get("tone", "")
    category = result.get("category", "")

    async with async_session_maker() as session:
        # Обновляем channel: category + last_update
        channel = await session.get(Channel, channel_id)
        if channel:
            channel.last_update = datetime.utcnow()
            # Обновляем category ТОЛЬКО если LLM определил его
            # и текущий category пустой (не перезаписываем Excel-категорию)
            if category and not channel.category:
                channel.category = category
                logger.info("Updated channel category: %s -> '%s'", channel_id, category)

        # Keywords сохраняются в keywords_cache
        kc = await session.get(KeywordsCache, channel_id)
        if not kc:
            kc = KeywordsCache(
                channel_id=channel_id,
                audience=audience,
                tone=tone,
                keywords_json=json.dumps(keywords),
                created_at=datetime.utcnow(),
            )
            session.add(kc)
        else:
            kc.audience = audience
            kc.tone = tone
            kc.keywords_json = json.dumps(keywords)
            kc.created_at = datetime.utcnow()

        await session.commit()

    logger.info("SAVE_ANALYSIS OK → channel_id=%s category='%s' keywords=%d", 
               channel_id, category, len(keywords))
