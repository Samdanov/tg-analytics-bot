# app/services/excel_importer.py
"""
Импорт каналов из Excel в БД.

АРХИТЕКТУРА ДАННЫХ:
- category (PRIMARY TOPIC) → channels.category (НЕ участвует в keywords!)
- keywords (SECONDARY) → keywords_cache.keywords_json (для TF-IDF similarity)

Keywords извлекаются ТОЛЬКО из title + description.
Лемматизация: слова приводятся к нормальной форме (единственное число, именительный падеж).
"""

import re
import pandas as pd
import pymorphy2
from typing import List, Optional, Set

from app.db.repo import save_channel
from app.services.llm.analyzer import save_analysis
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# МОРФОЛОГИЧЕСКИЙ АНАЛИЗАТОР (лемматизация)
# =============================================================================
_morph = None

def get_morph():
    """Lazy initialization морфологического анализатора."""
    global _morph
    if _morph is None:
        _morph = pymorphy2.MorphAnalyzer()
    return _morph


def lemmatize(word: str) -> str:
    """
    Приводит слово к нормальной форме (лемме).
    
    Примеры:
        продуктов → продукт
        рецепты → рецепт
        книги → книга
        культуры → культура
    """
    if not word:
        return word
    
    # Латиница - не лемматизируем (IT-термины, бренды)
    if re.fullmatch(r"[a-zA-Z0-9]+", word):
        return word.lower()
    
    # Кириллица - лемматизируем
    morph = get_morph()
    parsed = morph.parse(word)[0]
    return parsed.normal_form


# =============================================================================
# СТОП-СЛОВА
# =============================================================================

STOPWORDS_RU = {
    # Служебные слова
    "и", "в", "на", "к", "для", "о", "от", "по", "с", "за", "у",
    "это", "тот", "эта", "эти", "как", "но", "или", "да", "не",
    "мы", "вы", "они", "он", "она", "так", "же", "из", "про",
    "над", "под", "что", "то", "бы", "а", "ну", "все", "всем",
    "при", "без", "до", "если", "только", "уже", "ещё", "еще",
    "вот", "там", "тут", "здесь", "когда", "где", "кто", "чем",
    "быть", "есть", "было", "будет", "может", "могут", "нужно",
    "очень", "более", "менее", "также", "тоже", "даже", "ведь",
    "свой", "своя", "свои", "своё", "наш", "наша", "наши", "ваш",
    "каждый", "каждая", "любой", "любая", "другой", "другая",
    "первый", "второй", "много", "мало", "больше", "меньше",
    "хороший", "хорошая", "плохой", "самый", "самая", "самое",
    "который", "которая", "которое", "которые", "через", "после",
    "перед", "между", "около", "потому", "почему", "зачем",
    "куда", "откуда", "сюда", "туда", "никогда", "всегда",
    "сейчас", "теперь", "раньше", "позже", "скоро", "давно",
    # Telegram/маркетинг мусор
    "канал", "телеграм", "подписаться", "подписка", "ссылка",
    "чат", "бот", "админ", "пост", "посты", "реклама",
    "новый", "новая", "новое", "новости", "лучший", "лучшая",
    "официальный", "топ", "буст", "донат", "поддержка",
    "владелец", "менеджер", "контакт", "прайс", "сотрудничество",
    "вопросам", "вопросы", "вопрос", "ответ", "ответы",
    "пишите", "писать", "написать", "связь", "связи",
    "информация", "информации", "сайт", "страница",
    "регистрация", "заявление", "заявка", "номер", "адрес",
    "бесплатно", "бесплатный", "бесплатная",
}

STOPWORDS_EN = {
    # Служебные
    "the", "and", "for", "with", "you", "your", "from", "this", "that",
    "are", "was", "were", "been", "have", "has", "had", "will", "would",
    "can", "could", "should", "may", "might", "must", "shall",
    "our", "their", "its", "his", "her", "all", "any", "some", "one",
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "more", "most", "other", "into", "over", "under", "again", "further",
    "then", "once", "here", "there", "both", "each", "few", "such",
    "only", "same", "than", "very", "just", "also", "now", "about",
    # Платформы (мусор)
    "instagram", "youtube", "tiktok", "twitter", "facebook", "vkontakte",
    "whatsapp", "viber", "telegram", "boosty", "patreon", "taplink",
    "spotify", "soundcloud", "dzen", "rutube", "linkedin",
    # Telegram мусор
    "channel", "chat", "bot", "admin", "subscribe", "subscription",
    "link", "url", "https", "http", "www", "post", "posts",
    "news", "new", "best", "top", "official", "verified",
    "boost", "donate", "support", "owner", "manager", "contact",
    "price", "cooperation", "free", "click", "join", "follow", "share",
    "info", "information", "site", "website", "page",
    "gmail", "mail", "email", "phone", "send",
}

STOPWORDS = STOPWORDS_RU | STOPWORDS_EN

# Мусорные латинские слова (URL-фрагменты, сокращения)
GARBAGE_LATIN = {
    # URL-сокращатели и фрагменты
    "clck", "cutt", "link", "click", "href", "http", "https", "www",
    "utm", "ref", "src", "html", "php", "asp",
    # Соцсети username-фрагменты
    "inst", "insta", "tg", "vk", "fb", "tw", "yt",
    # Общий мусор
    "blog", "user", "admin", "test", "demo", "temp", "null", "none",
    "chat", "group", "channel", "official", "real", "original",
}

# =============================================================================
# WHITELIST КОРОТКИХ IT-ТЕРМИНОВ (< 4 символов)
# =============================================================================

WHITELIST_SHORT_TERMS = {
    # Языки программирования (3 символа)
    "sql", "php", "css", "xml", "lua", "cpp",
    # Технологии/системы (3 символа)
    "crm", "erp", "api", "sdk", "cms", "cdn", "vpn", "dns",
    "seo", "smm", "sap", "aws", "gcp", "nft",
    # 2 символа (очень важные термины)
    "ai", "ml", "bi", "it", "hr", "pr", "ip", "go",
    # Финансы
    "p2p", "b2b", "b2c",
    # 1C (латиница и кириллица)
    "1c", "1с",  # латинская c и русская с
}


# =============================================================================
# НОРМАЛИЗАЦИЯ КАТЕГОРИЙ (48 тем из Excel)
# =============================================================================

VALID_CATEGORIES = {
    "telegram",
    "бизнес и стартапы",
    "блоги",
    "букмекерство",
    "видео и фильмы",
    "даркнет",
    "дизайн",
    "для взрослых",
    "другое",
    "еда и кулинария",
    "здоровье и фитнес",
    "игры",
    "инстаграм",
    "интерьер и строительство",
    "искусство",
    "картинки и фото",
    "карьера",
    "книги",
    "криптовалюты",
    "курсы и гайды",
    "лингвистика",
    "маркетинг, pr, реклама",
    "медицина",
    "мода и красота",
    "музыка",
    "новости и сми",
    "образование",
    "познавательное",
    "политика",
    "право",
    "природа",
    "продажи",
    "психология",
    "путешествия",
    "религия",
    "рукоделие",
    "семья и дети",
    "софт и приложения",
    "спорт",
    "технологии",
    "транспорт",
    "цитаты",
    "шок-контент",
    "эзотерика",
    "экономика",
    "эротика",
    "юмор и развлечения",
    "не указана",
}


def normalize_category(raw_category: str) -> str:
    """
    Нормализует категорию к одной из 48 валидных тем.
    
    Returns:
        Нормализованная категория (lowercase) или "" если не найдена.
    """
    if not raw_category:
        return ""
    
    cleaned = raw_category.strip().lower()
    
    if not cleaned or cleaned in ("nan", "none"):
        return ""
    
    # Прямое совпадение
    if cleaned in VALID_CATEGORIES:
        return cleaned
    
    # Попытка найти похожую (на случай опечаток в Excel)
    # Простой поиск по вхождению
    for valid in VALID_CATEGORIES:
        if cleaned in valid or valid in cleaned:
            return valid
    
    # Не найдена - возвращаем пустую строку (или можно "другое")
    return ""


# =============================================================================
# ФИЛЬТРАЦИЯ МУСОРА
# =============================================================================

def is_valid_token(token: str) -> bool:
    """
    Проверяет, является ли токен валидным keyword.
    
    Разрешаем:
    - Кириллица ≥ 3 символов
    - Латиница ≥ 4 символов (IT-термины: python, excel, crm, api, saas)
    
    Отклоняем:
    - Стоп-слова
    - Username-подобные (заканчиваются на bot, содержат _ или цифры)
    - Смешанные кириллица+латиница
    - Слишком длинные (> 25)
    """
    if not token:
        return False
    
    token = token.lower().strip()
    
    # СНАЧАЛА проверяем whitelist (ai, ml, go, 1c, sql, crm, etc.)
    # Это позволяет коротким IT-терминам пройти
    if token in WHITELIST_SHORT_TERMS:
        return True
    
    # Стоп-слова
    if token in STOPWORDS:
        return False
    
    # Слишком короткие/длинные (whitelist уже проверен!)
    if len(token) < 3 or len(token) > 25:
        return False
    
    # Начинается с @ - username
    if token.startswith("@"):
        return False
    
    # Только цифры
    if token.isdigit():
        return False
    
    # Определяем тип токена
    is_cyrillic = bool(re.fullmatch(r"[а-яё]+", token))
    is_latin = bool(re.fullmatch(r"[a-z]+", token))
    
    # Смешанные (кроме whitelist) - мусор
    if not is_cyrillic and not is_latin:
        # Содержит цифры, подчеркивания или смесь алфавитов
        return False
    
    # Кириллица: минимум 3 символа
    if is_cyrillic and len(token) >= 3:
        return True
    
    # Латиница: минимум 4 символа
    if is_latin and len(token) >= 4:
        if token.endswith("bot"):
            return False
        if token in GARBAGE_LATIN:
            return False
        return True
    
    return False


# =============================================================================
# ИЗВЛЕЧЕНИЕ KEYWORDS
# =============================================================================

def extract_keywords(title: str, description: str, limit: int = 15, use_lemma: bool = True) -> List[str]:
    """
    Извлекает ЧИСТЫЕ keywords из title + description.
    
    Правила:
    1. Category НЕ участвует (хранится отдельно как PRIMARY TOPIC)
    2. Кириллица ≥ 3, латиница ≥ 4 символов
    3. Без частотной эвристики (одно слово = одно добавление)
    4. Username НЕ используется как fallback
    5. ЛЕММАТИЗАЦИЯ: слова приводятся к нормальной форме
       (единственное число, именительный падеж)
    
    Args:
        title: Название канала
        description: Описание канала
        limit: Максимум keywords
        use_lemma: Использовать лемматизацию (по умолчанию True)
    
    Returns:
        Список уникальных смысловых keywords в нормальной форме
    """
    seen: Set[str] = set()
    keywords: List[str] = []
    
    def add_token(token: str) -> bool:
        """Добавляет токен если валидный и уникальный (с лемматизацией)."""
        t = token.lower().strip()
        
        # Сначала проверяем валидность оригинального токена
        if not is_valid_token(t):
            return False
        
        # Лемматизация (только для кириллицы)
        if use_lemma:
            t = lemmatize(t)
        
        # Проверяем уникальность леммы
        if t in seen:
            return False
        
        # Дополнительная проверка после лемматизации (лемма может оказаться стоп-словом)
        if t in STOPWORDS:
            return False
        
        seen.add(t)
        keywords.append(t)
        return True
    
    def extract_tokens(text: str) -> list:
        """Извлекает токены: слова + IT-термины с цифрами (b2b, 1c, p2p)."""
        # Основные слова (кириллица/латиница)
        words = re.findall(r"[а-яёА-ЯЁa-zA-Z]+", text)
        # IT-термины с цифрами (b2b, 1c, p2p, etc.) - латиница + цифры
        tech_terms_latin = re.findall(r"[a-zA-Z0-9]+", text)
        # Специально для "1С" (кириллица) - цифры + кириллица
        tech_terms_cyrillic = re.findall(r"[0-9][а-яёА-ЯЁ]+|[а-яёА-ЯЁ]+[0-9]+", text)
        # Объединяем, сохраняя порядок появления
        result = []
        seen_local = set()
        for t in words + tech_terms_latin + tech_terms_cyrillic:
            t_lower = t.lower()
            if t_lower not in seen_local:
                seen_local.add(t_lower)
                result.append(t)
        return result
    
    # 1. TITLE (приоритет - название канала)
    if title and title.lower() not in ("nan", "none", ""):
        tokens = extract_tokens(title)
        for token in tokens:
            if len(keywords) >= limit:
                break
            add_token(token)
    
    # 2. DESCRIPTION (дополнение, без частотной эвристики!)
    if description and description.lower() not in ("nan", "none", ""):
        tokens = extract_tokens(description)
        for token in tokens:
            if len(keywords) >= limit:
                break
            add_token(token)
    
    return keywords


# =============================================================================
# ИМПОРТ ИЗ EXCEL
# =============================================================================

async def import_channels_from_excel(
    path: str,
    max_rows: Optional[int] = None,
    min_subscribers: int = 0,
):
    """
    Импорт каналов из Excel файла.
    
    Логика:
    - category → channels.category (PRIMARY TOPIC, не в keywords!)
    - keywords → keywords_cache.keywords_json (только title + description)
    - Если keywords < 2 и description пустой → канал не участвует в similarity
    """
    logger.info("[IMPORT] читаю Excel: %s", path)
    
    df = pd.read_excel(path, header=1)
    
    if max_rows:
        df = df.iloc[:max_rows]
    
    total_rows = len(df)
    logger.info("[IMPORT] строк к обработке: %s", total_rows)
    
    # Статистика
    imported = 0
    imported_with_keywords = 0
    skipped_no_username = 0
    skipped_low_subs = 0
    skipped_low_quality = 0
    
    for idx, row in df.iterrows():
        # Username
        username = str(row.get("username") or "").strip()
        username = username.replace("@", "").replace("https://t.me/", "").replace("http://t.me/", "")
        
        if not username:
            skipped_no_username += 1
            continue
        
        # Title / Description / Category
        title = str(row.get("title") or "").strip()
        description = str(row.get("description") or "").strip()
        category = str(row.get("category") or "").strip()
        
        # Нормализация
        if not title or title.lower() in ("nan", "none"):
            title = ""
        if not description or description.lower() in ("nan", "none"):
            description = ""
        
        # Нормализация category к одной из 48 валидных тем
        category = normalize_category(category)
        
        # Subscribers
        try:
            subscribers = int(row.get("subscribers") or 0)
        except (ValueError, TypeError):
            subscribers = 0
        
        if subscribers < min_subscribers:
            skipped_low_subs += 1
            continue
        
        # =================================================================
        # ИЗВЛЕЧЕНИЕ KEYWORDS (только из title + description!)
        # Category НЕ участвует - это PRIMARY TOPIC
        # =================================================================
        keywords = extract_keywords(title, description, limit=15)
        
        # =================================================================
        # ПРОВЕРКА КАЧЕСТВА
        # Если keywords < 2 и description пустой → low quality
        # =================================================================
        has_quality_content = len(keywords) >= 2 or bool(description.strip())
        
        if not has_quality_content:
            skipped_low_quality += 1
            # Канал сохраняем, но без keywords (не участвует в similarity)
            keywords = []
        
        # =================================================================
        # СОХРАНЕНИЕ В БД
        # =================================================================
        try:
            channel_id = await save_channel({
                "username": username,
                "title": title or username,  # fallback для title
                "description": description,
                "subscribers": subscribers,
                "category": category,  # PRIMARY TOPIC - отдельно!
            })
        except Exception as e:
            logger.error("[IMPORT] ошибка сохранения @%s: %s", username, e)
            continue
        
        # Keywords сохраняем только если есть контент
        if keywords:
            try:
                await save_analysis(channel_id, {
                    "audience": "",
                    "keywords": keywords
                })
                imported_with_keywords += 1
            except Exception as e:
                logger.error("[IMPORT] ошибка keywords_cache @%s: %s", username, e)
        
        imported += 1
        if imported % 5000 == 0:
            logger.info("[IMPORT] прогресс: %s/%s (с keywords: %s)", 
                       imported, total_rows, imported_with_keywords)
    
    # Итоговая статистика
    logger.info("=" * 60)
    logger.info("[IMPORT] ГОТОВО")
    logger.info("[IMPORT] Импортировано каналов: %s", imported)
    logger.info("[IMPORT] С keywords (для similarity): %s", imported_with_keywords)
    logger.info("[IMPORT] Пропущено без username: %s", skipped_no_username)
    logger.info("[IMPORT] Пропущено мало подписчиков: %s", skipped_low_subs)
    logger.info("[IMPORT] Low quality (без keywords): %s", skipped_low_quality)
    logger.info("=" * 60)
    
    return imported
