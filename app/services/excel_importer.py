# app/services/excel_importer.py

import re
import pandas as pd
from typing import List, Optional, Set

from app.db.repo import save_channel
from app.services.llm.analyzer import save_analysis
from app.core.logging import get_logger

logger = get_logger(__name__)


# Стоп-слова для фильтрации
STOPWORDS = {
    "и","в","на","к","для","о","от","по","с","за","у",
    "это","тот","эта","эти","как","но","или","да","не",
    "мы","вы","они","он","она","так","же","из","про",
    "над","под","что","то","бы","а","ну", "все", "всем",
    "канал", "telegram", "https", "http", "nan", "none",
    "the","and","for","with","you","your","from","this","that"
}

# Маппинг категорий на тематические ключевые слова
CATEGORY_KEYWORDS = {
    "Новости и СМИ": ["новости", "СМИ", "медиа", "журналистика", "информация", "репортаж", "события"],
    "Политика": ["политика", "власть", "государство", "выборы", "партии", "законы", "правительство"],
    "Бизнес и стартапы": ["бизнес", "стартап", "предпринимательство", "инвестиции", "финансы", "компании"],
    "Криптовалюты": ["криптовалюта", "биткоин", "блокчейн", "трейдинг", "крипто", "токены", "DeFi"],
    "Экономика": ["экономика", "финансы", "рынок", "банки", "инвестиции", "валюта", "макроэкономика"],
    "Технологии": ["технологии", "IT", "программирование", "разработка", "софт", "гаджеты", "инновации"],
    "Маркетинг, PR, реклама": ["маркетинг", "реклама", "PR", "продвижение", "SMM", "бренд", "таргет"],
    "Образование": ["образование", "обучение", "курсы", "студенты", "школа", "университет", "знания"],
    "Карьера": ["карьера", "работа", "вакансии", "HR", "резюме", "профессия", "трудоустройство"],
    "Право": ["право", "юриспруденция", "законы", "адвокат", "суд", "юрист", "правовая"],
    "Медицина": ["медицина", "здоровье", "врачи", "лечение", "болезни", "фармацевтика", "клиника"],
    "Здоровье и Фитнес": ["здоровье", "фитнес", "спорт", "тренировки", "питание", "ЗОЖ", "похудение"],
    "Психология": ["психология", "ментальное здоровье", "саморазвитие", "отношения", "терапия"],
    "Еда и кулинария": ["еда", "кулинария", "рецепты", "готовка", "ресторан", "продукты", "кухня"],
    "Путешествия": ["путешествия", "туризм", "отдых", "страны", "отели", "авиабилеты", "travel"],
    "Мода и красота": ["мода", "красота", "стиль", "одежда", "косметика", "бьюти", "fashion"],
    "Интерьер и строительство": ["интерьер", "строительство", "дизайн", "ремонт", "недвижимость", "дом"],
    "Авто": ["авто", "автомобили", "машины", "транспорт", "водители", "автосервис", "тюнинг"],
    "Спорт": ["спорт", "футбол", "хоккей", "баскетбол", "тренировки", "соревнования", "фитнес"],
    "Музыка": ["музыка", "песни", "артисты", "концерты", "альбомы", "треки", "аудио"],
    "Видео и фильмы": ["видео", "фильмы", "кино", "сериалы", "YouTube", "стриминг", "контент"],
    "Игры": ["игры", "геймеры", "киберспорт", "gaming", "PS", "Xbox", "PC игры", "мобильные игры"],
    "Книги": ["книги", "литература", "чтение", "писатели", "романы", "библиотека", "издательство"],
    "Искусство": ["искусство", "арт", "живопись", "музеи", "выставки", "творчество", "галерея"],
    "Дизайн": ["дизайн", "графика", "UI/UX", "визуал", "креатив", "брендинг", "иллюстрация"],
    "Познавательное": ["познавательное", "наука", "факты", "интересное", "образование", "лайфхаки"],
    "Блоги": ["блог", "личный", "автор", "мнение", "лайфстайл", "контент", "посты"],
    "Юмор": ["юмор", "мемы", "шутки", "смешное", "приколы", "развлечения", "comedy"],
    "Цитаты": ["цитаты", "мотивация", "мудрость", "афоризмы", "вдохновение", "слова"],
    "Картинки и фото": ["картинки", "фото", "изображения", "фотография", "визуал", "арт"],
    "Лингвистика": ["лингвистика", "языки", "английский", "перевод", "словарь", "изучение языков"],
    "Эзотерика": ["эзотерика", "астрология", "гороскоп", "таро", "мистика", "духовность"],
    "Религия": ["религия", "вера", "церковь", "духовность", "молитва", "священное"],
    "Для взрослых": ["взрослый контент", "18+", "adult"],
    "Букмекерство": ["букмекер", "ставки", "спортивные прогнозы", "betting", "тотализатор"],
    "Даркнет": ["даркнет", "darknet", "анонимность", "privacy"],
    "Telegram": ["telegram", "боты", "каналы", "мессенджер", "стикеры"],
    "Инстаграм": ["instagram", "инстаграм", "соцсети", "блогеры", "influencer"],
    "Курсы и гайды": ["курсы", "гайды", "обучение", "туториал", "инструкции"],
    "Другое": ["разное", "микс", "контент"],
}


def extract_keywords_v2(
    title: str,
    description: str,
    category: str,
    limit: int = 20
) -> List[str]:
    """
    Улучшенное извлечение keywords:
    1. Категория → тематические ключевые слова (приоритет!)
    2. Title/Description → дополнительные слова
    """
    keywords: List[str] = []
    seen: Set[str] = set()
    
    def add_keyword(kw: str):
        kw_lower = kw.lower().strip()
        if kw_lower and kw_lower not in seen and kw_lower not in STOPWORDS and len(kw_lower) >= 3:
            seen.add(kw_lower)
            keywords.append(kw)
    
    # 1. Добавляем keywords из категории (ПРИОРИТЕТ!)
    category_clean = category.strip() if category and category.lower() != "nan" else ""
    if category_clean:
        # Сама категория как keyword
        add_keyword(category_clean)
        
        # Тематические слова для категории
        category_kws = CATEGORY_KEYWORDS.get(category_clean, [])
        for kw in category_kws:
            add_keyword(kw)
    
    # 2. Извлекаем значимые слова из title (не мусор!)
    if title and title.lower() != "nan":
        # Только слова длиннее 4 символов и не username
        title_tokens = re.findall(r"[а-яёА-ЯЁa-zA-Z]{4,}", title)
        for t in title_tokens[:5]:  # Максимум 5 слов из title
            if t.lower() not in STOPWORDS and not t.startswith("@"):
                add_keyword(t)
    
    # 3. Из description берём только если мало keywords
    if len(keywords) < 8 and description and description.lower() != "nan":
        desc_tokens = re.findall(r"[а-яёА-ЯЁa-zA-Z]{5,}", description)
        freq = {}
        for t in desc_tokens:
            t_lower = t.lower()
            if t_lower not in STOPWORDS:
                freq[t] = freq.get(t, 0) + 1
        
        # Топ-5 частых слов из description
        sorted_tokens = sorted(freq.items(), key=lambda x: -x[1])[:5]
        for t, _ in sorted_tokens:
            add_keyword(t)
    
    return keywords[:limit]


# Старая функция для совместимости
def extract_keywords(text: str, limit: int = 20) -> List[str]:
    if not text:
        return []
    text = text.lower()
    tokens = re.findall(r"[a-zа-яё0-9]{3,}", text)

    freq = {}
    for t in tokens:
        if t in STOPWORDS:
            continue
        freq[t] = freq.get(t, 0) + 1

    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:limit]]


async def import_channels_from_excel(
    path: str,
    max_rows: Optional[int] = None,
    min_subscribers: int = 0,
    use_v2: bool = True  # Использовать улучшенный алгоритм
):
    """
    Импорт каналов из Excel файла.
    
    Args:
        path: Путь к Excel файлу
        max_rows: Максимум строк для импорта
        min_subscribers: Минимум подписчиков
        use_v2: Использовать улучшенный алгоритм keywords (рекомендуется!)
    """
    logger.info("[IMPORT] читаю Excel: %s", path)

    df = pd.read_excel(path, header=1)

    if max_rows:
        df = df.iloc[:max_rows]

    logger.info("[IMPORT] строк к обработке: %s", len(df))
    logger.info("[IMPORT] алгоритм keywords: %s", "V2 (категории)" if use_v2 else "V1 (legacy)")

    imported = 0
    skipped_no_username = 0
    skipped_low_subs = 0

    for _, row in df.iterrows():

        username = str(row.get("username") or "").strip()
        username = username.replace("@", "").replace("https://t.me/", "").replace("http://t.me/", "")

        if not username:
            skipped_no_username += 1
            continue

        title = str(row.get("title") or "").strip()
        description = str(row.get("description") or "").strip()
        category = str(row.get("category") or "").strip()

        if not title or title.lower() == "nan":
            title = username
        if not description or description.lower() == "nan":
            description = ""

        try:
            subscribers = int(row.get("subscribers") or 0)
        except Exception:
            subscribers = 0

        if subscribers < min_subscribers:
            skipped_low_subs += 1
            continue

        # Выбор алгоритма keywords
        if use_v2:
            keywords = extract_keywords_v2(title, description, category, limit=20)
        else:
            full_text = f"{title} {description} {category} {username}"
            keywords = extract_keywords(full_text, limit=20)

        if not keywords:
            keywords = [category] if category and category.lower() != "nan" else [username]

        try:
            channel_id = await save_channel({
                "username": username,
                "title": title,
                "description": description,
                "subscribers": subscribers
            })
        except Exception as e:
            logger.error("[IMPORT] ошибка сохранения @%s: %s", username, e)
            continue

        try:
            await save_analysis(channel_id, {
                "audience": "",
                "keywords": keywords
            })
        except Exception as e:
            logger.error("[IMPORT] ошибка keywords_cache @%s: %s", username, e)

        imported += 1
        if imported % 5000 == 0:
            logger.info("[IMPORT] импортировано каналов: %s", imported)

    logger.info("[IMPORT] готово. Импортировано: %s", imported)
    logger.info("[IMPORT] пропущено без username: %s, мало подписчиков: %s", 
                skipped_no_username, skipped_low_subs)
    return imported
