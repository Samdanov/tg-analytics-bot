"""
Main entry point with Dependency Injection

Использует новую архитектуру с DI Container.
"""

import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

from app.core.container import get_container
from app.core.logging import setup_logging
from app.services.telegram_parser import init_telegram, shutdown_telegram
from app.bot.middlewares.error_handler import IgnoreForbiddenMiddleware
from app.bot.middlewares.subscription import SubscriptionMiddleware


async def main():
    """
    Главная функция бота с DI.
    
    Использует новую архитектуру:
    - DI Container для зависимостей
    - Use Cases для бизнес-логики
    - Repositories для данных
    - Domain services для правил
    """
    # Инициализация
    setup_logging()
    
    # Получаем контейнер
    container = get_container()
    config = container.config
    logger = container.logger(__name__)
    
    logger.info("Starting ORBITA bot with DI architecture...")
    
    # Валидация конфигурации
    try:
        from app.core.config import validate_config
        validate_config()
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    # Создаем бота
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Middlewares
    dp.message.middleware(IgnoreForbiddenMiddleware())
    dp.callback_query.middleware(IgnoreForbiddenMiddleware())
    
    # Subscription middleware (проверка лимитов)
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    # Выбор версии handlers (через переменную окружения)
    use_di_handlers = os.getenv("USE_DI_HANDLERS", "true").lower() == "true"
    
    if use_di_handlers:
        logger.info("Using DI handlers (workflow_di.py)")
        from app.bot.handlers.workflow_di import router as workflow_router
    else:
        logger.info("Using legacy handlers (workflow.py)")
        from app.bot.handlers.workflow import router as workflow_router
    
    # Subscription commands router
    from app.bot.handlers.subscription import router as subscription_router
    
    dp.include_router(subscription_router)
    dp.include_router(workflow_router)
    
    # Start command
    @dp.message(Command("start"))
    async def start_handler(message: Message):
        """Обработчик команды /start."""
        try:
            from app.services.user_service import UserService
            
            # Получаем/создаем пользователя
            user_id = message.from_user.id
            user = await UserService.get_or_create_user(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name
            )
            
            # Определяем лимиты
            if user.subscription_type == "free":
                limit_text = f"🆓 <b>Бесплатный тариф:</b> {user.queries_used}/{user.queries_limit} запросов, до 100 каналов"
            elif user.subscription_type in ("premium", "admin"):
                limit_text = "💎 <b>Premium:</b> Безлимитные запросы, до 500 каналов"
            else:
                limit_text = ""
            
            await message.answer(
                "🤖 <b>ОРБИТА — Аналитик Telegram-каналов</b>\n\n"
                "Просто отправь мне:\n"
                "• 📱 <b>Пост из канала</b> (перешли или дай мне ссылку)\n"
                "• 🔗 <b>Ссылку на канал</b> (t.me/username или @username)\n"
                "• 🌐 <b>Ссылку на сайт</b>\n\n"
                "Я автоматически найду похожие каналы и отправлю отчёт!\n\n"
                f"{limit_text}\n\n"
                "📊 <b>Команды:</b>\n"
                "• /stats - ваша статистика\n"
                "• /health - состояние системы"
            )
        except TelegramForbiddenError:
            return
    
    # Health check command (для мониторинга)
    @dp.message(Command("health"))
    async def health_handler(message: Message):
        """Health check endpoint."""
        try:
            stats = await container.repository.get_statistics()
            
            await message.answer(
                "🟢 <b>Статус системы: OK</b>\n\n"
                f"📊 <b>Статистика БД:</b>\n"
                f"• Всего каналов: {stats['total_channels']}\n"
                f"• Проанализировано: {stats['channels_analyzed']}\n"
                f"• Постов: {stats['total_posts']}\n\n"
                f"🏗️ <b>Архитектура:</b>\n"
                f"• DI Container: {'✅ Активен' if use_di_handlers else '⚠️ Legacy mode'}\n"
                f"• Domain Layer: ✅\n"
                f"• Schemas Layer: ✅\n"
                f"• Repositories: ✅\n"
                f"• Use Cases: ✅"
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            await message.answer(f"🔴 <b>Ошибка:</b> {e}")
    
    # Инициализация Telegram клиента
    logger.info("Initializing Telegram client...")
    await init_telegram()
    
    # Запуск бота
    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down...")
        await shutdown_telegram()


if __name__ == "__main__":
    asyncio.run(main())

