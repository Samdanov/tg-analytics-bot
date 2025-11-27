import asyncio

from app.services.discovery import ChannelDiscovery, save_usernames_to_db
from app.services.telegram_parser import init_telegram

TOPICS = [
    # Новости и медиа
    "новости", "политика", "общество", "город", "москва",
    "санкт петербург", "рф", "экономика", "мировые новости",
    "breaking news", "world news", "news today",

    # Финансы и бизнес
    "финансы", "экономика", "деньги", "инвестиции", "акции",
    "крипта", "cryptocurrency", "bitcoin", "forex", "crypto news",
    "бизнес", "маркетинг", "smm", "advertising",

    # IT и технологии
    "айти", "it", "программирование", "python", "javascript",
    "технологии", "техно", "ai", "artificial intelligence",
    "machine learning", "нейросети", "datascience",

    # Работа и карьера
    "работа", "вакансии", "job", "it jobs", "hr", "офер",

    # Личностное развитие
    "психология", "отношения", "мотивация", "саморазвитие",

    # Путешествия
    "путешествия", "туризм", "travel", "europe travel",

    # Развлечения
    "юмор", "мемы", "мем", "memes", "fun", "entertainment",

    # Культура / lifestyle
    "красота", "мода", "lifestyle", "еда", "рецепты", "кулинария",

    # Спорт
    "спорт", "футбол", "sport news", "football",

    # Творчество
    "фото", "искусство", "art", "design", "дизайн"
]


LIMIT_PER_TOPIC = 50


async def main():
    print("[INIT] Запуск Telegram-клиента")
    await init_telegram()

    discovery = ChannelDiscovery()
    all_usernames: set[str] = set()

    for topic in TOPICS:
        print(f"[DISCOVERY] Тема: {topic}")
        usernames = await discovery.search_topic(topic, LIMIT_PER_TOPIC)
        print(f"  найдено username: {len(usernames)}")
        all_usernames.update(usernames)
        await asyncio.sleep(1.0)  # анти-флуд

    print(f"[TOTAL] всего уникальных username: {len(all_usernames)}")
    await save_usernames_to_db(list(all_usernames))
    print("[DONE] Импорт завершён")


if __name__ == "__main__":
    asyncio.run(main())
