import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError

from app.core.config import config, validate_config
from app.core.logging import setup_logging
from app.services.telegram_parser import init_telegram, shutdown_telegram

from app.bot.middlewares.error_handler import IgnoreForbiddenMiddleware
from app.bot.handlers.fetch import router as fetch_router
from app.bot.handlers.add_channel import router as add_channel_router
from app.bot.handlers.analyze import router as analyze_router
from app.bot.handlers.export import router as export_router
from app.bot.handlers.workflow import router as workflow_router


async def main():
    setup_logging()
    validate_config()

    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.message.middleware(IgnoreForbiddenMiddleware())
    dp.callback_query.middleware(IgnoreForbiddenMiddleware())

    dp.include_router(fetch_router)
    dp.include_router(add_channel_router)
    dp.include_router(analyze_router)
    dp.include_router(export_router)
    dp.include_router(workflow_router)

    @dp.message(Command("start"))
    async def start_handler(message: Message):
        try:
            await message.answer("Готов к работе. Кидай ссылку на канал, пост или сайт.")
        except TelegramForbiddenError:
            return

    await init_telegram()

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown_telegram()


if __name__ == "__main__":
    asyncio.run(main())
