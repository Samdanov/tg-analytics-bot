"""
Subscription Handlers - команды для управления подписками и статистикой.

Команды для пользователей:
- /stats - просмотр статистики

Команды для админов:
- /admin_grant <user_id> <type> - выдать подписку
- /admin_reset <user_id> - сбросить счетчик запросов
- /admin_ban <user_id> - забанить пользователя
- /admin_unban <user_id> - разбанить пользователя
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta

from app.services.user_service import UserService
from app.bot.styles import Icons
from app.core.logging import get_logger

router = Router()
logger = get_logger(__name__)

# Список админов (Telegram user IDs)
# TODO: Перенести в конфиг или БД
ADMIN_IDS = [
    5563773415,  # Ваш Telegram ID
    # Добавьте другие ID сюда
    # Например: 123456789
]


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id in ADMIN_IDS


@router.message(Command("stats"))
async def stats_handler(message: Message):
    """
    Показывает статистику пользователя.
    
    Использование: /stats
    """
    user_id = message.from_user.id
    
    stats = await UserService.get_user_stats(user_id)
    
    if not stats:
        # Создаем пользователя
        await UserService.get_or_create_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        stats = await UserService.get_user_stats(user_id)
    
    subscription_emoji = {
        "free": "🆓",
        "premium": "💎",
        "admin": "👑"
    }
    
    sub_type = stats["subscription_type"]
    emoji = subscription_emoji.get(sub_type, "❓")
    
    # Форматируем лимит запросов
    if stats["queries_limit"] == -1:
        limit_text = "∞ (безлимит)"
    else:
        limit_text = str(stats["queries_limit"])
    
    # Форматируем дату окончания подписки
    expires_text = "—"
    if stats["subscription_expires_at"]:
        expires = stats["subscription_expires_at"]
        if expires > datetime.utcnow():
            days_left = (expires - datetime.utcnow()).days
            expires_text = f"{expires.strftime('%d.%m.%Y')} ({days_left} дн.)"
        else:
            expires_text = f"❌ Истекла {expires.strftime('%d.%m.%Y')}"
    
    text = (
        f"{Icons.ORBIT} <b>Ваша статистика</b>\n\n"
        f"👤 <b>Пользователь:</b> @{stats['username'] or 'N/A'}\n"
        f"{emoji} <b>Подписка:</b> {sub_type.upper()}\n"
        f"📅 <b>Действует до:</b> {expires_text}\n\n"
        f"📊 <b>Использование:</b>\n"
        f"• Запросов: {stats['queries_used']} / {limit_text}\n"
        f"• Макс. каналов: {stats['max_channels']}\n\n"
        f"📅 <b>Регистрация:</b> {stats['created_at'].strftime('%d.%m.%Y')}\n"
    )
    
    if sub_type == "free":
        text += (
            f"\n💎 <b>Хотите больше?</b>\n"
            f"Получите Premium:\n"
            f"• Безлимитные запросы\n"
            f"• До 500 каналов в отчете\n"
            f"• Приоритетная поддержка"
        )
    
    await message.answer(text)


@router.message(Command("admin_grant"))
async def admin_grant_handler(message: Message):
    """
    Выдает подписку пользователю.
    
    Использование: /admin_grant <user_id> <type> [days]
    
    Примеры:
        /admin_grant 123456789 premium 30
        /admin_grant 987654321 admin
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ Использование: /admin_grant <user_id> <type> [days]\n\n"
            "Примеры:\n"
            "  /admin_grant 123456789 premium 30\n"
            "  /admin_grant 987654321 admin"
        )
        return
    
    try:
        target_user_id = int(args[1])
        subscription_type = args[2].lower()
        
        if subscription_type not in ("free", "premium", "admin"):
            await message.answer("❌ Тип подписки должен быть: free, premium, admin")
            return
        
        # Дата окончания подписки
        expires_at = None
        if len(args) >= 4:
            days = int(args[3])
            expires_at = datetime.utcnow() + timedelta(days=days)
        
        # Создаем пользователя если не существует
        await UserService.get_or_create_user(user_id=target_user_id)
        
        # Устанавливаем подписку
        success = await UserService.set_subscription(
            user_id=target_user_id,
            subscription_type=subscription_type,
            expires_at=expires_at
        )
        
        if success:
            expires_text = f" до {expires_at.strftime('%d.%m.%Y')}" if expires_at else ""
            await message.answer(
                f"✅ Подписка выдана!\n\n"
                f"Пользователь: {target_user_id}\n"
                f"Тип: {subscription_type.upper()}{expires_text}"
            )
            logger.info(f"Admin {message.from_user.id} granted {subscription_type} to {target_user_id}")
        else:
            await message.answer("❌ Ошибка при выдаче подписки")
    
    except ValueError:
        await message.answer("❌ Неверный формат. user_id и days должны быть числами.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.exception("Error in admin_grant")


@router.message(Command("admin_reset"))
async def admin_reset_handler(message: Message):
    """
    Сбрасывает счетчик запросов пользователя.
    
    Использование: /admin_reset <user_id>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /admin_reset <user_id>")
        return
    
    try:
        target_user_id = int(args[1])
        
        success = await UserService.reset_queries(target_user_id)
        
        if success:
            await message.answer(f"✅ Счетчик запросов сброшен для {target_user_id}")
            logger.info(f"Admin {message.from_user.id} reset queries for {target_user_id}")
        else:
            await message.answer(f"❌ Пользователь {target_user_id} не найден")
    
    except ValueError:
        await message.answer("❌ user_id должен быть числом")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.exception("Error in admin_reset")


@router.message(Command("admin_info"))
async def admin_info_handler(message: Message):
    """
    Показывает информацию о пользователе.
    
    Использование: /admin_info <user_id>
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав.")
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /admin_info <user_id>")
        return
    
    try:
        target_user_id = int(args[1])
        
        stats = await UserService.get_user_stats(target_user_id)
        
        if not stats:
            await message.answer(f"❌ Пользователь {target_user_id} не найден")
            return
        
        # Форматируем лимит
        if stats["queries_limit"] == -1:
            limit_text = "∞ (безлимит)"
        else:
            limit_text = str(stats["queries_limit"])
        
        # Форматируем дату окончания
        expires_text = "—"
        if stats["subscription_expires_at"]:
            expires_text = stats["subscription_expires_at"].strftime('%d.%m.%Y %H:%M')
        
        text = (
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"<b>ID:</b> {stats['user_id']}\n"
            f"<b>Username:</b> @{stats['username'] or 'N/A'}\n"
            f"<b>Подписка:</b> {stats['subscription_type'].upper()}\n"
            f"<b>Действует до:</b> {expires_text}\n\n"
            f"<b>Запросов:</b> {stats['queries_used']} / {limit_text}\n"
            f"<b>Макс. каналов:</b> {stats['max_channels']}\n\n"
            f"<b>Статус:</b> {'✅ Активен' if stats['is_active'] else '❌ Неактивен'}\n"
            f"<b>Забанен:</b> {'❌ Да' if stats['is_banned'] else '✅ Нет'}\n\n"
            f"<b>Регистрация:</b> {stats['created_at'].strftime('%d.%m.%Y %H:%M')}"
        )
        
        await message.answer(text)
    
    except ValueError:
        await message.answer("❌ user_id должен быть числом")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.exception("Error in admin_info")


@router.message(Command("admin_help"))
async def admin_help_handler(message: Message):
    """Показывает список admin команд."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав.")
        return
    
    text = (
        "👑 <b>Admin команды:</b>\n\n"
        "<b>/admin_grant</b> <code>&lt;user_id&gt; &lt;type&gt; [days]</code>\n"
        "Выдать подписку\n"
        "Примеры:\n"
        "• <code>/admin_grant 123 premium 30</code>\n"
        "• <code>/admin_grant 456 admin</code>\n\n"
        "<b>/admin_reset</b> <code>&lt;user_id&gt;</code>\n"
        "Сбросить счетчик запросов\n\n"
        "<b>/admin_info</b> <code>&lt;user_id&gt;</code>\n"
        "Информация о пользователе\n\n"
        "<b>/admin_help</b>\n"
        "Эта справка\n\n"
        "<b>Типы подписок:</b>\n"
        "• <code>free</code> - 10 запросов, до 100 каналов\n"
        "• <code>premium</code> - безлимит, до 500 каналов\n"
        "• <code>admin</code> - безлимит, до 500 каналов"
    )
    
    await message.answer(text)
