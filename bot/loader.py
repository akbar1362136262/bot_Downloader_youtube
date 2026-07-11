from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings


def create_bot() -> Bot:
    session = AiohttpSession(
        timeout=120,
    )
    if settings.PROXY_ENABLED and settings.PROXY_URL:
        session.proxy = settings.PROXY_URL
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )


bot = create_bot()
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
