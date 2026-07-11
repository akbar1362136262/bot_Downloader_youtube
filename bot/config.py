import sys
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).parent / ".env")
    return str(Path(__file__).resolve().parent.parent / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_get_env_path(),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    PROXY_URL: str = ""
    PROXY_ENABLED: bool = False

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def split_admin_ids(cls, v: str | int | list[int] | None) -> list[int]:
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return []

    @field_validator("PROXY_ENABLED", mode="before")
    @classmethod
    def parse_proxy_enabled(cls, v: str | bool | int | None) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        if isinstance(v, int):
            return v == 1
        return False
    MAX_FILE_SIZE: int = 2_097_152_000
    DOWNLOAD_TIMEOUT: int = 300
    LOG_LEVEL: str = "DEBUG"
    LOG_FILE: str = "logs/bot.log"

    DOWNLOAD_DIR: Path = Path(__file__).resolve().parent.parent / "downloads"
    LOG_DIR: Path = Path(__file__).resolve().parent.parent / "logs"


settings = Settings()
