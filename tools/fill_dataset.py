import asyncio

from app.services.discovery import ChannelDiscovery, save_usernames_to_db
from app.services.telegram_parser import init_telegram

TOPICS = [
    "финансы", "экономика", "крипта", "биткоин",
    "спорт", "футбол", "новости", "юмор",
    "отношения", "психология", "образование",
    "здоровье", "фитнес", "рецепты", "кулинария",
    "мода", "красота", "технологии", "айти",
    "программирование", "дизайн", "маркетинг",
    "бизнес", "авто", "путешествия", "фильмы",
    "книги", "приколы"
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
