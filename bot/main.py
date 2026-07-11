from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from loguru import logger

from bot.config import settings
from bot.loader import bot, dp
from bot.utils.helpers import ensure_directories

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def setup_logging() -> None:
    ensure_directories()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.remove()
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    logger.add(
        settings.LOG_FILE,
        format=log_format,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )


async def on_startup() -> None:
    logger.info("Starting Downloader Bot...")
    ensure_directories()
    bot_info = await bot.get_me()
    logger.info(f"Bot: @{bot_info.username} (ID: {bot_info.id})")

    from bot.utils.downloader import HAS_FFMPEG

    if not HAS_FFMPEG:
        logger.warning(
            "FFmpeg not found! Video will use combined formats (audio included). "
            "Audio downloads will be in native format (m4a/webm). "
            "Install FFmpeg for best quality & mp3 conversion."
        )
    if settings.PROXY_ENABLED and settings.PROXY_URL:
        logger.info(f"Proxy enabled: {settings.PROXY_URL}")
    else:
        logger.info("Proxy not configured. If Telegram API is unreachable, set PROXY_URL in .env")


async def on_shutdown() -> None:
    logger.info("Shutting down Downloader Bot...")
    await bot.session.close()


async def main() -> None:
    setup_logging()

    from bot.handlers import start, link_handler, quality_choice, cookies_handler, errors

    dp.include_router(errors.router)
    dp.include_router(start.router)
    dp.include_router(cookies_handler.router)
    dp.include_router(link_handler.router)
    dp.include_router(quality_choice.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
