from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from typing import Callable, Awaitable, Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class IgnoreForbiddenMiddleware(BaseMiddleware):
    """
    Игнорирует ошибки Forbidden/BadRequest (бот заблокирован, chat not found и т.п.),
    чтобы не ронять обработку обновлений.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning("Ignored Telegram error: %s", e)
            return None
