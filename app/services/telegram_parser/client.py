from telethon import TelegramClient
from core.config import config

session_name = "tg_parser"

client = TelegramClient(
    session=session_name,
    api_id=config.telegram_api_id,
    api_hash=config.telegram_api_hash
)
