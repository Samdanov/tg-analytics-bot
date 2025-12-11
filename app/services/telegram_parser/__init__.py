from .client import client, start_client, stop_client, is_started


async def init_telegram():
    await start_client()


async def shutdown_telegram():
    await stop_client()
