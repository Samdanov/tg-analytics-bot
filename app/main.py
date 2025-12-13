import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

from app.core.config import config, validate_config
from app.core.logging import setup_logging
from app.services.telegram_parser import init_telegram, shutdown_telegram

from app.bot.middlewares.error_handler import IgnoreForbiddenMiddleware
from app.bot.handlers.workflow import router as workflow_router


async def main():
    setup_logging()
    validate_config()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.message.middleware(IgnoreForbiddenMiddleware())
    dp.callback_query.middleware(IgnoreForbiddenMiddleware())

    # Основной workflow: обработка постов и сайтов, отправленных напрямую в бота
    dp.include_router(workflow_router)

    @dp.message(Command("start"))
    async def start_handler(message: Message):
        try:
            await message.answer(
                "🤖 <b>ОРБИТА — Аналитик Telegram-каналов</b>\n\n"
                "Просто отправь мне:\n"
                "• 📱 <b>Пост из канала</b> (перешли или дай мне ссылку)\n"
                "• 🔗 <b>Ссылку на канал</b> (t.me/username или @username)\n"
                "• 🌐 <b>Ссылку на сайт</b>\n\n"
                "Я автоматически найду похожие каналы и отправлю отчёт!"
            )
        except TelegramForbiddenError:
            return

    await init_telegram()

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown_telegram()


if __name__ == "__main__":
    asyncio.run(main())
