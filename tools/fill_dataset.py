import asyncio
from app.services.discovery import ChannelDiscovery
from app.services.import_channels_service import ImportChannelsService

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
    discovery = ChannelDiscovery()

    all_usernames = set()

    for topic in TOPICS:
        print(f"[DISCOVERY] {topic}")
        usernames = await discovery.search_topic(topic, LIMIT_PER_TOPIC)
        print(f"  найдено: {len(usernames)}")

        all_usernames.update(usernames)

        await asyncio.sleep(1.0)  # анти-флуд

    print(f"[TOTAL] всего уникальных username: {len(all_usernames)}")

    await ImportChannelsService.import_usernames(list(all_usernames))

    print("[DONE] Импорт завершён!")


if __name__ == "__main__":
    asyncio.run(main())
