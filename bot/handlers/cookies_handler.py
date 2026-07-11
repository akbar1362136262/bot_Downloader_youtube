from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Document
from loguru import logger

from bot.config import settings

router = Router()


@router.message(Command("cookies"))
async def cookies_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "<b>Cookie Setup</b>\n\n"
        "Send a cookies.txt file to enable downloads.\n\n"
        "<b>How to export cookies:</b>\n"
        "1. Install 'Get cookies.txt' extension in Chrome/Kiwi\n"
        "2. Log into the site (YouTube or Instagram)\n"
        "3. Click the extension icon → Export\n"
        "4. Send the .txt file here\n\n"
        "The bot detects YouTube vs Instagram cookies automatically."
    )
    await message.answer(text)


@router.message(F.document)
async def handle_cookies_file(message: Message, state: FSMContext) -> None:
    await state.clear()
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.endswith(".txt"):
        await message.answer("Please send a .txt cookies file.")
        return

    file = await message.bot.get_file(doc.file_id)

    name_lower = doc.file_name.lower()
    content = None

    if "youtube" in name_lower or "youtu" in name_lower:
        dest = settings.DOWNLOAD_DIR / "youtube_cookies.txt"
    elif "instagram" in name_lower:
        dest = settings.DOWNLOAD_DIR / "instagram_cookies.txt"
    else:
        await message.bot.download_file(file.file_path, destination=settings.DOWNLOAD_DIR / "cookies_temp.txt")
        content = (settings.DOWNLOAD_DIR / "cookies_temp.txt").read_text(encoding="utf-8")
        if "instagram.com" in content:
            dest = settings.DOWNLOAD_DIR / "instagram_cookies.txt"
            (settings.DOWNLOAD_DIR / "cookies_temp.txt").rename(dest)
        elif "youtube.com" in content or "youtu.be" in content:
            dest = settings.DOWNLOAD_DIR / "youtube_cookies.txt"
            (settings.DOWNLOAD_DIR / "cookies_temp.txt").rename(dest)
        else:
            (settings.DOWNLOAD_DIR / "cookies_temp.txt").unlink()
            await message.answer(
                "Could not detect platform. Name your file "
                "youtube_cookies.txt or instagram_cookies.txt and try again."
            )
            return

    if content is None:
        await message.bot.download_file(file.file_path, destination=dest)
        content = dest.read_text(encoding="utf-8")

    if "# Netscape HTTP Cookie File" not in content:
        dest.unlink(missing_ok=True)
        await message.answer(
            "Invalid cookies file. Export using 'Get cookies.txt' extension "
            "in Netscape format."
        )
        return

    logger.info(f"Cookies saved to {dest}")
    platform = "YouTube" if "youtube" in str(dest) else "Instagram"
    await message.answer(
        f"{platform} cookies saved! Now you can download {platform} content."
    )
