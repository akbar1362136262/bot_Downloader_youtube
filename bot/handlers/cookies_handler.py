from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document
from loguru import logger

from bot.config import settings

router = Router()


@router.message(Command("cookies"))
async def cookies_help(message: Message) -> None:
    text = (
        "<b>Instagram Cookie Setup</b>\n\n"
        "To download Instagram content, the bot needs Instagram login cookies.\n\n"
        "<b>Option 1: Upload cookies.txt file</b>\n"
        "1. Open Instagram in your phone browser (Kiwi Browser supports extensions)\n"
        "2. Install 'Get cookies.txt' extension from Chrome Web Store\n"
        "3. Log into Instagram and tap the extension icon → Export\n"
        "4. Send the exported .txt file to this bot\n\n"
        "<b>Option 2: Run as Administrator (Windows)</b>\n"
        "- Close Chrome, run the bot exe as Administrator\n"
        "- The bot will extract cookies automatically\n\n"
        "<b>Option 3: Desktop browser</b>\n"
        "- Log into Instagram on your computer's Chrome\n"
        "- Install 'Get cookies.txt' extension\n"
        "- Export cookies and place next to the exe file\n\n"
        "Send the .txt file now to upload cookies."
    )
    await message.answer(text)


@router.message(F.document)
async def handle_cookies_file(message: Message) -> None:
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.endswith(".txt"):
        await message.answer("Please send a .txt cookies file.")
        return

    file = await message.bot.get_file(doc.file_id)
    dest = settings.DOWNLOAD_DIR / "instagram_cookies.txt"
    await message.bot.download_file(file.file_path, destination=dest)

    content = dest.read_text(encoding="utf-8")
    if "# Netscape HTTP Cookie File" not in content and "instagram" not in content.lower():
        dest.unlink()
        await message.answer(
            "Invalid cookies file. Please export cookies from Instagram using "
            "'Get cookies.txt' extension while logged into Instagram."
        )
        return

    logger.info(f"Instagram cookies saved to {dest}")
    await message.answer(
        "Instagram cookies saved successfully! Now you can download Instagram content."
    )
