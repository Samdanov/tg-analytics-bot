from telethon import TelegramClient
from app.core.config import config

session_name = "tg_parser"

client = TelegramClient(
    session=session_name,
    api_id=config.telegram_api_id,
    api_hash=config.telegram_api_hash
)

_started = False


async def start_client():
    global _started
    if _started:
        return
    await client.start()
    _started = True


async def stop_client():
    global _started
    if not _started:
        return
    await client.disconnect()
    _started = False


def is_started() -> bool:
    return _started
