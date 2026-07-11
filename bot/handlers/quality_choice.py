from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from loguru import logger

from bot.config import settings
from bot.keyboards.inline import main_menu_keyboard, cancel_keyboard
from bot.states.user_states import DownloadStates
from bot.utils.downloader import DownloaderFactory
from bot.utils.helpers import cleanup_file

router = Router()

PROGRESS_MESSAGE = (
    "<b>Downloading...</b>\n\n"
    "📁 <b>Title:</b> {title}\n"
    "⏳ <b>Progress:</b> {percent}\n"
    "⚡ <b>Speed:</b> {speed}\n"
    "⏱ <b>ETA:</b> {eta}"
)


@router.callback_query(lambda c: c.data.startswith("video_res:"))
async def handle_video_quality(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    format_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    url = data["url"]
    platform = data["platform"]
    title = data.get("title", "Unknown")

    status_msg = await callback.message.edit_text(
        PROGRESS_MESSAGE.format(
            title=title,
            percent="0.0%",
            speed="N/A",
            eta="N/A",
        ),
        reply_markup=cancel_keyboard(),
    )

    try:
        downloader = DownloaderFactory.get_downloader(url)
        if not downloader:
            await status_msg.edit_text("Error: could not initialize downloader.")
            return

        progress_task = asyncio.create_task(
            _update_progress(status_msg, downloader, title)
        )

        file_path = await downloader.download(url, format_id, is_audio=False)
        progress_task.cancel()

        if file_path and file_path.exists():
            await _send_video_file(callback, file_path, title, data, status_msg)
        else:
            await status_msg.edit_text(
                "Download failed. The file may be too large or unavailable.",
                reply_markup=main_menu_keyboard(),
            )
    except Exception as e:
        logger.error(f"Video download error: {e}")
        await status_msg.edit_text(f"Download error: {e}", reply_markup=main_menu_keyboard())
    finally:
        await state.clear()


@router.callback_query(lambda c: c.data.startswith("audio_quality:"))
async def handle_audio_quality(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    data = await state.get_data()
    url = data["url"]
    platform = data["platform"]
    title = data.get("title", "Unknown")

    status_msg = await callback.message.edit_text(
        PROGRESS_MESSAGE.format(
            title=title,
            percent="0.0%",
            speed="N/A",
            eta="N/A",
        ),
        reply_markup=cancel_keyboard(),
    )

    try:
        downloader = DownloaderFactory.get_downloader(url)
        if not downloader:
            await status_msg.edit_text("Error: could not initialize downloader.")
            return

        progress_task = asyncio.create_task(
            _update_progress(status_msg, downloader, title)
        )

        file_path = await downloader.download(url, "bestaudio", is_audio=True)
        progress_task.cancel()

        if file_path and file_path.exists():
            await _send_audio_file(callback, file_path, title, status_msg)
        else:
            await status_msg.edit_text(
                "Download failed. The file may be too large or unavailable.",
                reply_markup=main_menu_keyboard(),
            )
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        await status_msg.edit_text(f"Download error: {e}", reply_markup=main_menu_keyboard())
    finally:
        await state.clear()


async def _update_progress(
    status_msg: Message,
    downloader: Any,
    title: str,
) -> None:
    while True:
        await asyncio.sleep(2)
        progress = getattr(downloader, "progress", None)
        if not progress:
            continue
        try:
            await status_msg.edit_text(
                PROGRESS_MESSAGE.format(
                    title=title[:50],
                    percent=progress.percent,
                    speed=progress.speed,
                    eta=progress.eta,
                ),
                reply_markup=cancel_keyboard(),
            )
        except Exception:
            pass


async def _upload_with_retry(
    upload_fn: Any,
    file_path: Path,
    max_retries: int = 3,
) -> bool:
    for attempt in range(max_retries):
        try:
            await upload_fn()
            return True
        except Exception as e:
            logger.warning(f"Upload attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    return False


async def _send_video_file(
    callback: CallbackQuery,
    file_path: Path,
    title: str,
    data: dict[str, Any],
    status_msg: Message,
) -> None:
    file_size = file_path.stat().st_size
    caption = f"<b>{title[:100]}</b>"

    if file_size > settings.MAX_FILE_SIZE:
        await status_msg.edit_text(
            f"File too large ({file_size / 1024 / 1024:.1f} MB). "
            "Maximum allowed: 2 GB.",
            reply_markup=main_menu_keyboard(),
        )
        await cleanup_file(file_path)
        return

    await status_msg.edit_text("Uploading video...")

    input_file = FSInputFile(str(file_path))
    success = await _upload_with_retry(
        lambda: callback.message.answer_video(
            video=input_file,
            caption=caption,
            supports_streaming=True,
        ),
        file_path,
    )

    if not success:
        logger.warning("Video upload failed, sending as document")
        input_file = FSInputFile(str(file_path))
        success = await _upload_with_retry(
            lambda: callback.message.answer_document(
                document=input_file,
                caption=caption,
            ),
            file_path,
        )

    await cleanup_file(file_path)
    if success:
        await status_msg.edit_text(
            "Download completed!",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await status_msg.edit_text(
            "Upload failed after multiple retries. Check network (VPN/proxy may be needed).",
            reply_markup=main_menu_keyboard(),
        )


async def _send_audio_file(
    callback: CallbackQuery,
    file_path: Path,
    title: str,
    status_msg: Message,
) -> None:
    file_size = file_path.stat().st_size
    caption = f"<b>{title[:100]}</b>"

    if file_size > settings.MAX_FILE_SIZE:
        await status_msg.edit_text(
            f"File too large ({file_size / 1024 / 1024:.1f} MB). "
            "Maximum allowed: 2 GB.",
            reply_markup=main_menu_keyboard(),
        )
        await cleanup_file(file_path)
        return

    await status_msg.edit_text("Uploading audio...")

    input_file = FSInputFile(str(file_path))
    success = await _upload_with_retry(
        lambda: callback.message.answer_audio(
            audio=input_file,
            caption=caption,
            title=title[:50],
        ),
        file_path,
    )

    if not success and file_path.suffix != ".mp3":
        logger.warning("Audio upload failed, sending as document")
        input_file = FSInputFile(str(file_path))
        success = await _upload_with_retry(
            lambda: callback.message.answer_document(
                document=input_file,
                caption=caption,
            ),
            file_path,
        )

    await cleanup_file(file_path)
    if success:
        await status_msg.edit_text(
            "Download completed!",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await status_msg.edit_text(
            "Upload failed after multiple retries. Check network (VPN/proxy may be needed).",
            reply_markup=main_menu_keyboard(),
        )
