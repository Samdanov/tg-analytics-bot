import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import Command

from core.config import config

async def main():
    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start_handler(message: Message):
        await message.answer("Готов к работе. Кидай ссылку на канал, пост или сайт.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())