"""
User Service - управление пользователями и подписками.

Обрабатывает:
- Регистрацию новых пользователей
- Проверку лимитов
- Учет использованных запросов
- Управление подписками
"""

from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.database import async_session_maker
from app.db.models import User
from app.core.logging import get_logger

logger = get_logger(__name__)


# Константы лимитов
FREE_QUERIES_LIMIT = 10
FREE_MAX_CHANNELS = 100

PREMIUM_QUERIES_LIMIT = -1  # Безлимит
PREMIUM_MAX_CHANNELS = 500

ADMIN_QUERIES_LIMIT = -1  # Безлимит
ADMIN_MAX_CHANNELS = 500


class UserService:
    """Сервис для работы с пользователями."""
    
    @staticmethod
    async def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> User:
        """
        Получает пользователя или создает нового.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username (без @)
            first_name: Имя пользователя
        
        Returns:
            User object
        """
        async with async_session_maker() as session:
            # Пытаемся найти пользователя (используем telegram_id)
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Обновляем username/first_name если изменились (если колонки существуют)
                try:
                    if username and user.username != username:
                        user.username = username
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name
                    # Обновляем last_activity_at (если колонка существует)
                    user.last_activity_at = datetime.utcnow()
                except Exception:
                    # Колонки не существуют - пропускаем
                    pass
                
                await session.commit()
                await session.refresh(user)
                return user
            
            # Создаем нового пользователя
            new_user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                subscription_type="free",
                queries_used=0,
                queries_limit=FREE_QUERIES_LIMIT,
                is_active=True,
                is_banned=False,
                created_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            
            try:
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                
                logger.info(f"Created new user: {user_id} (@{username}), type=free, limit={FREE_QUERIES_LIMIT}")
                return new_user
            
            except IntegrityError:
                # Race condition - пользователь уже создан
                await session.rollback()
                result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                return result.scalar_one()
    
    @staticmethod
    async def check_query_limit(user_id: int) -> Tuple[bool, str, int, int]:
        """
        Проверяет, может ли пользователь сделать запрос.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            (can_query, message, used, limit)
            - can_query: может ли делать запрос
            - message: сообщение для пользователя
            - used: использовано запросов
            - limit: лимит запросов (-1 = безлимит)
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Пользователь еще не создан - разрешаем (создастся автоматически)
                return True, "", 0, FREE_QUERIES_LIMIT
            
            # Используем методы с дефолтами
            is_banned = user.get_is_banned()
            is_active = user.get_is_active()
            queries_used = user.get_queries_used()
            queries_limit = user.get_queries_limit()
            
            # Проверка бана
            if is_banned:
                return False, "❌ Ваш аккаунт заблокирован. Обратитесь в поддержку.", queries_used, queries_limit
            
            if not is_active:
                return False, "❌ Ваш аккаунт неактивен. Обратитесь в поддержку.", queries_used, queries_limit
            
            # Безлимитная подписка
            if queries_limit == -1:
                return True, "", queries_used, -1
            
            # Проверка лимита
            if queries_used >= queries_limit:
                msg = (
                    f"⚠️ <b>Лимит исчерпан!</b>\n\n"
                    f"Использовано: {queries_used}/{queries_limit} запросов\n\n"
                    f"💎 <b>Получите Premium для безлимитных запросов!</b>\n"
                    f"• Неограниченное количество анализов\n"
                    f"• До 500 каналов в отчете\n"
                    f"• Приоритетная поддержка"
                )
                return False, msg, queries_used, queries_limit
            
            return True, "", queries_used, queries_limit
    
    @staticmethod
    async def increment_query_usage(user_id: int) -> bool:
        """
        Увеличивает счетчик использованных запросов.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True если успешно
        """
        async with async_session_maker() as session:
            try:
                # Пытаемся обновить queries_used (если колонка существует)
                result = await session.execute(
                    update(User)
                    .where(User.telegram_id == user_id)
                    .values(
                        queries_used=User.queries_used + 1,
                        last_activity_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                rows = result.rowcount
                if rows > 0:
                    logger.info(f"Incremented query usage for user {user_id}")
                    return True
                return False
            except Exception as e:
                # Колонки не существуют - просто логируем и продолжаем
                await session.rollback()
                logger.debug(f"Could not increment query usage (columns may not exist): {e}")
                return True  # Возвращаем True, чтобы не блокировать работу
    
    @staticmethod
    async def get_max_channels_for_user(user_id: int) -> int:
        """
        Возвращает максимальное количество каналов для пользователя.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Максимальное количество каналов (100 для free, 500 для premium)
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User.subscription_type).where(User.user_id == user_id)
            )
            subscription_type = result.scalar_one_or_none()
            
            if not subscription_type or subscription_type == "free":
                return FREE_MAX_CHANNELS
            elif subscription_type in ("premium", "admin"):
                return PREMIUM_MAX_CHANNELS
            
            return FREE_MAX_CHANNELS
    
    @staticmethod
    async def set_subscription(
        user_id: int,
        subscription_type: str,
        queries_limit: int = None,
        expires_at: datetime = None
    ) -> bool:
        """
        Устанавливает тип подписки для пользователя.
        
        Args:
            user_id: Telegram user ID
            subscription_type: "free", "premium", "admin"
            queries_limit: Лимит запросов (None = по умолчанию для типа)
            expires_at: Дата окончания подписки
        
        Returns:
            True если успешно
        """
        # Определяем лимиты по умолчанию
        if queries_limit is None:
            if subscription_type == "free":
                queries_limit = FREE_QUERIES_LIMIT
            elif subscription_type in ("premium", "admin"):
                queries_limit = -1  # Безлимит
        
        async with async_session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == user_id)
                .values(
                    subscription_type=subscription_type,
                    queries_limit=queries_limit,
                    subscription_expires_at=expires_at
                )
            )
            await session.commit()
            
            rows = result.rowcount
            if rows > 0:
                logger.info(
                    f"Updated subscription for user {user_id}: "
                    f"type={subscription_type}, limit={queries_limit}"
                )
                return True
            return False
    
    @staticmethod
    async def reset_queries(user_id: int) -> bool:
        """
        Сбрасывает счетчик использованных запросов.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            True если успешно
        """
        async with async_session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == user_id)
                .values(queries_used=0)
            )
            await session.commit()
            
            rows = result.rowcount
            if rows > 0:
                logger.info(f"Reset queries for user {user_id}")
                return True
            return False
    
    @staticmethod
    async def get_user_stats(user_id: int) -> Optional[dict]:
        """
        Получает статистику пользователя.
        
        Args:
            user_id: Telegram user ID
        
        Returns:
            Словарь со статистикой или None
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            subscription_type = user.get_subscription_type()
            
            return {
                "user_id": user.telegram_id,
                "username": user.username,
                "subscription_type": subscription_type,
                "queries_used": user.get_queries_used(),
                "queries_limit": user.get_queries_limit(),
                "max_channels": FREE_MAX_CHANNELS if subscription_type == "free" else PREMIUM_MAX_CHANNELS,
                "is_active": user.get_is_active(),
                "is_banned": user.get_is_banned(),
                "created_at": user.created_at,
                "subscription_expires_at": user.subscription_expires_at
            }
