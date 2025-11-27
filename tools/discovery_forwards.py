import asyncio

from app.services.discovery_forwards_service import DiscoveryForwardsService
from app.services.telegram_parser import init_telegram


async def main():
    print("[DISCOVERY 3.0] Через пересланные сообщения")

    await init_telegram()

    service = DiscoveryForwardsService()

    ids = await service.get_forwarded_channel_ids()
    print(f"[INFO] Найдено forwarded каналов по ID: {len(ids)}")

    usernames = await service.resolve_ids_to_usernames(ids)
    print(f"[INFO] Получено username: {len(usernames)}")

    added = await service.save_new_usernames(usernames)
    print(f"[DONE] Добавлено новых каналов: {added}")


if __name__ == "__main__":
    asyncio.run(main())
