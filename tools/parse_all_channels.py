import asyncio
from app.services.bulk_channel_parser import BulkChannelParser
from app.services.telegram_parser import init_telegram


async def main():
    print("[INIT] Запуск Telegram-клиента")
    await init_telegram()

    parser = BulkChannelParser(post_limit=50)

    await parser.parse_all()


if __name__ == "__main__":
    asyncio.run(main())
