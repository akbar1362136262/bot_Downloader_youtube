from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from bot.config import settings


async def cleanup_file(file_path: Path) -> None:
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete {file_path}: {e}")


async def cleanup_downloads() -> None:
    for p in settings.DOWNLOAD_DIR.iterdir():
        if p.is_file():
            await cleanup_file(p)


def ensure_directories() -> None:
    settings.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)


def format_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size //= 1024
    return f"{size:.1f} TB"


def check_disk_space(file_size: int) -> bool:
    total, used, free = shutil.disk_usage(settings.DOWNLOAD_DIR)
    return free > file_size * 2
