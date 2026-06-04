import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from bot.handlers import common, master, manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(master.router)
    dp.include_router(manager.router)

    logger.info("SimplyFlow бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())