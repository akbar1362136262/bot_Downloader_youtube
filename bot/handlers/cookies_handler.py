import base64

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


def _save_cookies(content: str, platform: str) -> str:
    filename = f"{platform}_cookies.txt"
    dest = settings.DOWNLOAD_DIR / filename
    dest.write_text(content, encoding="utf-8")
    logger.info(f"Cookies saved to {dest}")
    return str(dest)


@router.message(F.document)
async def handle_cookies_file(message: Message, state: FSMContext) -> None:
    await state.clear()
    doc: Document = message.document
    if not doc.file_name or not doc.file_name.endswith(".txt"):
        await message.answer("Please send a .txt cookies file.")
        return

    file = await message.bot.get_file(doc.file_id)
    temp = settings.DOWNLOAD_DIR / "cookies_temp.txt"
    await message.bot.download_file(file.file_path, destination=temp)
    content = temp.read_text(encoding="utf-8")
    temp.unlink(missing_ok=True)

    if "# Netscape HTTP Cookie File" not in content:
        await message.answer(
            "Invalid cookies file. Export using 'Get cookies.txt' extension "
            "in Netscape format."
        )
        return

    name_lower = doc.file_name.lower()
    if "instagram" in name_lower or "instagram" in content.lower():
        platform = "instagram"
    elif "youtube" in name_lower or "youtube" in content.lower() or "youtu.be" in content:
        platform = "youtube"
    else:
        await message.answer(
            "Could not detect platform. Name your file "
            "youtube_cookies.txt or instagram_cookies.txt and try again."
        )
        return

    _save_cookies(content, platform)
    b64 = base64.b64encode(content.encode()).decode()

    msg = (
        f"{'YouTube' if platform == 'youtube' else 'Instagram'} cookies saved!\n\n"
        f"<b>For Railway persistence</b>, add this to your Railway Variables:\n\n"
        f"<code>{platform.upper()}_COOKIES_B64</code> = <code>{b64[:50]}...{b64[-20:]}</code>\n\n"
        f"(Full value copied below - copy it entirely)"
    )

    await message.answer(msg)

    chunks = []
    for i in range(0, len(b64), 4000):
        chunks.append(b64[i:i + 4000])
    for chunk in chunks:
        await message.answer(f"<code>{chunk}</code>")
