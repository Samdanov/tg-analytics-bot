import asyncio

from app.services.discovery_mentions_service import DiscoveryMentionsService


async def main():
    print("[DISCOVERY 2.0] Ищем новые каналы через упоминания...")

    service = DiscoveryMentionsService()

    usernames = await service.extract_usernames_from_posts()
    print(f"[INFO] Найдено упоминаний: {len(usernames)}")

    added = await service.save_new_usernames(list(usernames))

    print(f"[DONE] Добавлено новых каналов: {added}")


if __name__ == "__main__":
    asyncio.run(main())
