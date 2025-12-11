import asyncio
from typing import Tuple

from sqlalchemy import text

from app.db.database import async_session_maker
from app.services.telegram_parser.client import client, start_client, stop_client
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_db(timeout: float = 5.0) -> Tuple[bool, str]:
    try:
        async with asyncio.timeout(timeout):
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
        return True, "DB OK"
    except Exception as e:
        return False, f"DB error: {e}"


async def check_telegram(timeout: float = 10.0) -> Tuple[bool, str]:
    try:
        await asyncio.wait_for(start_client(), timeout=timeout)
        me = await asyncio.wait_for(client.get_me(), timeout=timeout)
        return True, f"Telegram OK: {getattr(me, 'id', None)}"
    except Exception as e:
        return False, f"Telegram error: {e}"
    finally:
        try:
            await asyncio.wait_for(stop_client(), timeout=timeout)
        except Exception:
            pass
