import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel
from telethon.errors import FloodWaitError, RpcError

from app.services.telegram_parser.client import client


class ChannelDiscovery:
    """
    Ищет каналы по словам через search_global.
    Возвращает список username каналов.
    """

    async def search_topic(self, topic: str, limit: int = 50):
        usernames = set()

        try:
            results = await client.search_global(topic)

            for item in results:
                if isinstance(item, Channel) and item.username:
                    usernames.add(item.username.lower())
                    if len(usernames) >= limit:
                        break

        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            return await self.search_topic(topic, limit)
        except RpcError:
            pass

        return list(usernames)
