from __future__ import annotations

import asyncio
import re
import shutil
from pathlib import Path
from typing import Any, Optional

import yt_dlp
from loguru import logger

from bot.config import settings
from bot.utils.cookies import ensure_instagram_cookies, ensure_youtube_cookies


def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


HAS_FFMPEG = check_ffmpeg()


class DownloadProgress:
    def __init__(self) -> None:
        self.percent: str = "0.0"
        self.speed: str = "N/A"
        self.eta: str = "N/A"
        self.total_bytes: Optional[int] = None
        self.downloaded_bytes: int = 0

    def hook(self, d: dict[str, Any]) -> None:
        if d["status"] == "downloading":
            self.percent = d.get("_percent_str", "0.0").strip()
            self.speed = d.get("_speed_str", "N/A").strip()
            self.eta = d.get("_eta_str", "N/A").strip()
            self.downloaded_bytes = d.get("downloaded_bytes", 0)
            self.total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
        elif d["status"] == "finished":
            self.percent = "100.0"


class BaseDownloader:
    def __init__(self) -> None:
        self.progress: Optional[DownloadProgress] = None

    def _progress_hook(self, d: dict[str, Any]) -> None:
        if self.progress:
            self.progress.hook(d)

    def _common_opts(self) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noprogress": True,
            "no_color": True,
            "ignoreerrors": True,
            "outtmpl": str(settings.DOWNLOAD_DIR / "%(id)s.%(ext)s"),
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        }
        return opts


class YouTubeDownloader(BaseDownloader):
    def _cookies_opts(self) -> dict[str, Any]:
        opts: dict[str, Any] = {}
        cookies_file = ensure_youtube_cookies()
        if cookies_file:
            opts["cookiefile"] = cookies_file
        return opts

    def extract_info(self, url: str) -> dict[str, Any]:
        opts: dict[str, Any] = {
            **self._common_opts(),
            **self._cookies_opts(),
            "noplaylist": True,
            "ignoreerrors": False,
            "socket_timeout": 30,
            "geo_bypass": True,
            "geo_bypass_country": "US",
            "extractor_args": {
                "youtube": {
                    "skip": ["dash", "hls", "webpage"],
                    "player_client": ["android", "web"],
                },
            },
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    RESOLUTIONS = [
        ("144p", 144),
        ("240p", 240),
        ("360p", 360),
        ("480p", 480),
        ("720p", 720),
        ("1080p", 1080),
        ("2K", 1440),
        ("4K", 2160),
    ]

    def get_available_resolutions(self, info: dict[str, Any]) -> list[dict]:
        max_height = 0
        has_audio: bool = HAS_FFMPEG

        for f in info.get("formats", []):
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height", 0)
            has_v = vcodec != "none"
            has_a = acodec != "none"
            if has_v and has_a:
                has_audio = True
            if has_v:
                max_height = max(max_height, height or 0)

        available = []
        for label, h in self.RESOLUTIONS:
            if h <= max_height:
                note = ""
                if not HAS_FFMPEG and h > 720:
                    note = " (needs FFmpeg)"
                available.append({
                    "label": label + note,
                    "height": h,
                    "format_key": label.lower().replace("k", "k"),
                })
        return available

    async def download(
        self,
        url: str,
        format_id: str,
        is_audio: bool = False,
    ) -> Optional[Path]:
        self.progress = DownloadProgress()
        loop = asyncio.get_event_loop()

        cookies = self._cookies_opts()
        if is_audio:
            extractor_args = {"youtube": {"player_client": ["android", "web"]}}
            if HAS_FFMPEG:
                opts: dict[str, Any] = {
                    **self._common_opts(),
                    **cookies,
                    "noplaylist": True,
                    "extractor_args": extractor_args,
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                    "progress_hooks": [self._progress_hook],
                }
            else:
                opts = {
                    **self._common_opts(),
                    **cookies,
                    "noplaylist": True,
                    "extractor_args": extractor_args,
                    "format": "bestaudio/best",
                    "progress_hooks": [self._progress_hook],
                }
        else:
            height_map = {"144p": 144, "240p": 240, "360p": 360, "480p": 480, "720p": 720, "1080p": 1080, "2k": 1440, "4k": 2160}
            target_height = height_map.get(format_id, 720)
            extractor_args = {"youtube": {"player_client": ["android", "web"]}}

            if HAS_FFMPEG:
                fmt = f"bestvideo[height<={target_height}]+bestaudio/best[height<={target_height}]"
                opts = {
                    **self._common_opts(),
                    **cookies,
                    "noplaylist": True,
                    "extractor_args": extractor_args,
                    "format": fmt,
                    "merge_output_format": "mp4",
                    "progress_hooks": [self._progress_hook],
                }
            else:
                fmt = f"best[height<={target_height}]"
                opts = {
                    **self._common_opts(),
                    **cookies,
                    "noplaylist": True,
                    "extractor_args": extractor_args,
                    "format": fmt,
                    "progress_hooks": [self._progress_hook],
                }

        try:
            result = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(opts).download([url]),
            )
            if result != 0:
                return None

            info = self.extract_info(url)
            file_id = info.get("id", "")

            if is_audio and not HAS_FFMPEG:
                for p in settings.DOWNLOAD_DIR.iterdir():
                    if file_id in p.name and p.suffix in (".m4a", ".webm", ".mp3"):
                        return p

            ext = "mp3" if (is_audio and HAS_FFMPEG) else "mp4"
            file_path = settings.DOWNLOAD_DIR / f"{file_id}.{ext}"
            if file_path.exists():
                return file_path

            for p in settings.DOWNLOAD_DIR.iterdir():
                if file_id in p.name:
                    return p
            return None
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            return None

    @staticmethod
    def format_duration(seconds: Optional[float]) -> str:
        if not seconds:
            return "N/A"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @staticmethod
    def _format_size(bytes_val: Optional[float]) -> str:
        if not bytes_val:
            return "N/A"
        for unit in ("B", "KB", "MB", "GB"):
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"


class InstagramDownloader(BaseDownloader):
    RESOLUTIONS = YouTubeDownloader.RESOLUTIONS

    def _cookies_opts(self) -> dict[str, Any]:
        opts: dict[str, Any] = {}
        cookies_file = ensure_instagram_cookies()
        if cookies_file:
            opts["cookiefile"] = cookies_file
        else:
            opts["cookiesfrombrowser"] = ("chrome",)
            logger.info("Using yt-dlp's built-in cookie extraction as fallback")
        return opts

    def extract_info(self, url: str) -> dict[str, Any]:
        opts: dict[str, Any] = {
            **self._common_opts(),
            **self._cookies_opts(),
            "socket_timeout": 30,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def get_available_resolutions(self, info: dict[str, Any]) -> list[dict]:
        max_height = 0
        for f in info.get("formats", []):
            vcodec = f.get("vcodec", "none")
            if vcodec != "none":
                height = f.get("height", 0)
                if height:
                    max_height = max(max_height, height)

        available = []
        for label, h in self.RESOLUTIONS:
            if h <= max_height:
                available.append({
                    "label": label,
                    "height": h,
                    "format_key": label.lower().replace("k", "k"),
                })
        return available

    def get_formats(self, info: dict[str, Any]) -> tuple[list[dict], list[dict]]:
        video_formats: list[dict] = []
        audio_formats: list[dict] = []

        for f in info.get("formats", []):
            fmt_id = f.get("format_id", "")
            ext = f.get("ext", "")
            vcodec = f.get("vcodec", "none")
            filesize = f.get("filesize") or f.get("filesize_approx") or 0
            height = f.get("height", 0)
            tbr = f.get("tbr", 0)

            if vcodec != "none":
                label = f"{height or '?'}p | {ext} | {self._format_size(filesize)}"
                video_formats.append({
                    "format_id": fmt_id,
                    "label": label,
                    "ext": ext,
                    "height": height,
                    "filesize": filesize,
                })
            else:
                label = f"{tbr or 128}kbps | {ext} | {self._format_size(filesize)}"
                audio_formats.append({
                    "format_id": fmt_id,
                    "label": label,
                    "ext": ext,
                    "bitrate": tbr,
                    "filesize": filesize,
                })

        video_formats.sort(key=lambda x: x["height"] or 0, reverse=True)
        return video_formats, audio_formats

    async def _do_download(self, opts: dict[str, Any], url: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: yt_dlp.YoutubeDL(opts).download([url]),
            )
            return result == 0
        except Exception as e:
            logger.warning(f"Instagram download attempt failed: {e}")
            return False

    async def download(
        self,
        url: str,
        format_id: str = "best",
        is_audio: bool = False,
    ) -> Optional[Path]:
        try:
            self.progress = DownloadProgress()

            opts: dict[str, Any] = {
                **self._common_opts(),
                **self._cookies_opts(),
                "format": "best" if not is_audio else "bestaudio/best",
                "progress_hooks": [self._progress_hook],
            }
            if is_audio and HAS_FFMPEG:
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]

            ok = await self._do_download(opts, url)
            if not ok:
                return None

            ext = "mp3" if (is_audio and HAS_FFMPEG) else "mp4"
            for p in settings.DOWNLOAD_DIR.iterdir():
                if p.suffix in (f".{ext}", ".webm", ".jpg", ".png", ".m4a"):
                    return p
            return None
        except Exception as e:
            logger.error(f"Instagram download error: {e}")
            return None

    @staticmethod
    def _format_size(bytes_val: Optional[float]) -> str:
        if not bytes_val:
            return "N/A"
        for unit in ("B", "KB", "MB", "GB"):
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"


class DownloaderFactory:
    _registry: dict[str, type[BaseDownloader]] = {}

    @classmethod
    def register(cls, platform: str, downloader_cls: type[BaseDownloader]) -> None:
        cls._registry[platform] = downloader_cls

    @classmethod
    def get_downloader(cls, url: str) -> Optional[BaseDownloader]:
        for platform, dl_cls in cls._registry.items():
            pattern = getattr(dl_cls, "url_pattern", None)
            if pattern and re.search(pattern, url, re.IGNORECASE):
                return dl_cls()
        return None

    @classmethod
    def detect_platform(cls, url: str) -> Optional[str]:
        for platform, dl_cls in cls._registry.items():
            pattern = getattr(dl_cls, "url_pattern", None)
            if pattern and re.search(pattern, url, re.IGNORECASE):
                return platform
        return None


YouTubeDownloader.url_pattern = r"(youtube\.com|youtu\.be)"
InstagramDownloader.url_pattern = r"(instagram\.com|instagr\.am)"

if not HAS_FFMPEG:
    logger.warning(
        "FFmpeg not found. Video downloads will use combined formats (may be lower quality). "
        "Audio downloads will use native format (m4a/webm) instead of mp3. "
        "Install FFmpeg for best results: https://ffmpeg.org/download.html"
    )

DownloaderFactory.register("youtube", YouTubeDownloader)
DownloaderFactory.register("instagram", InstagramDownloader)
