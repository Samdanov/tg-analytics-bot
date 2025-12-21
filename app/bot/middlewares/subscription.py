"""
Subscription Middleware - проверка лимитов и подписок.

Автоматически:
- Регистрирует новых пользователей
- Проверяет лимиты перед анализом
- Блокирует забаненных пользователей
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.services.user_service import UserService
from app.core.logging import get_logger

logger = get_logger(__name__)


class SubscriptionMiddleware(BaseMiddleware):
    """
    Middleware для проверки подписки и лимитов.
    
    Применяется к:
    - Командам анализа
    - Callback кнопкам анализа
    """
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обрабатывает событие с проверкой лимитов.
        """
        # Получаем user_id
        if isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            username = event.from_user.username
            first_name = event.from_user.first_name
        else:
            # Неизвестный тип события - пропускаем
            return await handler(event, data)
        
        # Регистрируем/обновляем пользователя
        user = await UserService.get_or_create_user(
            user_id=user_id,
            username=username,
            first_name=first_name
        )
        
        # Добавляем пользователя в данные для handlers
        data["user"] = user
        
        # Проверяем, это запрос на анализ или нет
        is_analysis_request = False
        
        if isinstance(event, Message):
            # Проверяем, это команда /start или /health
            if event.text and event.text.startswith(("/start", "/health", "/stats", "/admin")):
                is_analysis_request = False
            # Проверяем, это отправленный контент (канал/сайт)
            elif event.text or event.forward_from_chat or event.photo or event.video:
                is_analysis_request = True
        
        elif isinstance(event, CallbackQuery):
            # Callback от кнопок анализа
            if event.data and event.data.startswith(("analyze:", "analyze_website|", "force_analyze:")):
                is_analysis_request = True
        
        # Если это не запрос на анализ - пропускаем проверку лимитов
        if not is_analysis_request:
            return await handler(event, data)
        
        # Проверяем лимиты
        can_query, message, used, limit = await UserService.check_query_limit(user_id)
        
        if not can_query:
            # Лимит исчерпан или пользователь забанен
            if isinstance(event, Message):
                await event.answer(message)
            elif isinstance(event, CallbackQuery):
                await event.answer("Лимит исчерпан!", show_alert=True)
                await event.message.answer(message)
            
            logger.warning(f"User {user_id} (@{username}) blocked: {message[:50]}")
            return  # Не вызываем handler
        
        # Пропускаем запрос дальше
        return await handler(event, data)
