import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

from core.config import config
from services.telegram_parser import init_telegram

# 👉 импортируем router
from bot.handlers.fetch import router as fetch_router
from bot.handlers.add_channel import router as add_channel_router


async def main():
    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    # 👉 подключаем router
    dp.include_router(fetch_router)
    dp.include_router(add_channel_router)


    @dp.message(Command("start"))
    async def start_handler(message: Message):
        await message.answer("Готов к работе. Кидай ссылку на канал, пост или сайт.")

    # 👉 запускаем Telethon
    await init_telegram()

    # 👉 запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())