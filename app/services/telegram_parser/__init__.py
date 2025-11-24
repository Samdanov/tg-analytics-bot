from .client import client

async def init_telegram():
    await client.start()
