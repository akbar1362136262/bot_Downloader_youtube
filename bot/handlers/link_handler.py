from __future__ import annotations

import asyncio
import re
from typing import Any

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from bot.keyboards.inline import (
    download_type_keyboard,
    video_resolution_keyboard,
    audio_quality_keyboard,
    cancel_keyboard,
)
from bot.states.user_states import DownloadStates
from bot.utils.downloader import DownloaderFactory, HAS_FFMPEG

router = Router()

URL_PATTERN = re.compile(
    r"https?://(?:www\.)?"
    r"(?:youtube\.com|youtu\.be|instagram\.com|instagr\.am)"
    r"/\S+",
    re.IGNORECASE,
)


def is_valid_url(text: str) -> bool:
    return bool(URL_PATTERN.match(text))


@router.message(DownloadStates.waiting_for_link, F.text)
async def handle_link(message: Message, state: FSMContext) -> None:
    url = message.text.strip()

    if not is_valid_url(url):
        await message.answer(
            "Invalid link. Please send a valid YouTube or Instagram link."
        )
        return

    platform = DownloaderFactory.detect_platform(url)
    if not platform:
        await message.answer("Unsupported platform. Please send a YouTube or Instagram link.")
        return

    await state.update_data(url=url, platform=platform)
    await state.set_state(DownloadStates.choosing_quality)

    await message.answer(
        "What would you like to download?",
        reply_markup=download_type_keyboard(),
    )


@router.message(DownloadStates.waiting_for_link, ~F.document)
async def handle_non_text(message: Message) -> None:
    await message.answer("Please send a text link.")


@router.callback_query(lambda c: c.data.startswith("dl_type:"))
async def handle_download_type(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    dl_type = callback.data.split(":", 1)[1]
    data = await state.get_data()
    url = data["url"]
    platform = data["platform"]

    await state.update_data(dl_type=dl_type)
    await state.set_state(DownloadStates.downloading)

    status_msg = await callback.message.edit_text(
        "Processing your link... Please wait.",
        reply_markup=cancel_keyboard(),
    )

    try:
        downloader = DownloaderFactory.get_downloader(url)
        if not downloader:
            await status_msg.edit_text("Unsupported platform.")
            return

        info = await _extract_info_async(downloader, url)

        title = info.get("title") or info.get("id", "Unknown")
        duration = info.get("duration")

        if dl_type == "video":
            resolutions = downloader.get_available_resolutions(info)

            if not resolutions:
                await status_msg.edit_text("No video resolutions found.")
                return

            await state.update_data(
                resolutions=resolutions,
                title=title,
                duration=duration,
                info_dict=info,
            )
            msg = "Select video quality:"
            if not HAS_FFMPEG:
                msg += "\n\n⚠️ 720p+ needs FFmpeg for best quality"
            await status_msg.edit_text(
                msg,
                reply_markup=video_resolution_keyboard(resolutions),
            )
        else:
            audio_fmts = []
            for f in info.get("formats", []):
                vcodec = f.get("vcodec", "none")
                acodec = f.get("acodec", "none")
                if vcodec == "none" and acodec != "none":
                    ext = f.get("ext", "")
                    abr = f.get("abr", 0)
                    filesize = f.get("filesize") or f.get("filesize_approx") or 0
                    audio_fmts.append({
                        "format_id": f.get("format_id", ""),
                        "label": f"{abr or 128}kbps | {ext}",
                        "ext": ext,
                        "bitrate": abr,
                        "filesize": filesize,
                    })

            if not audio_fmts:
                audio_fmts = [{
                    "format_id": "bestaudio",
                    "label": "Best Audio (automatic)",
                    "ext": "mp3",
                    "bitrate": 192,
                    "filesize": 0,
                }]

            await state.update_data(
                audio_formats=audio_fmts,
                title=title,
                duration=duration,
                info_dict=info,
            )
            await status_msg.edit_text(
                "Select audio quality:",
                reply_markup=audio_quality_keyboard(audio_fmts[:10]),
            )

    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await status_msg.edit_text(f"Error: {e}")
    finally:
        await state.clear()


async def _extract_info_async(downloader: Any, url: str) -> dict:
    loop = asyncio.get_event_loop()
    try:
        future = loop.run_in_executor(None, downloader.extract_info, url)
        info = await asyncio.wait_for(future, timeout=60.0)
        if not info:
            raise RuntimeError("yt-dlp returned no data. The video may be private or unavailable.")
        return info
    except asyncio.TimeoutError:
        logger.warning(f"Extract info timed out for URL: {url}")
        raise TimeoutError("Request timed out (60s). Try again or use a shorter video.")
    except Exception as e:
        logger.error(f"Extract info error for {url}: {e}")
        raise
