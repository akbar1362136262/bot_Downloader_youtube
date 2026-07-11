from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def platform_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="YouTube", callback_data="platform:youtube")
    builder.button(text="Instagram", callback_data="platform:instagram")
    builder.adjust(2)
    return builder.as_markup()


def video_resolution_keyboard(resolutions: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in resolutions:
        builder.button(
            text=r["label"],
            callback_data=f"video_res:{r['format_key']}",
        )
    builder.button(text="Cancel", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()


def audio_quality_keyboard(formats: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for f in formats:
        label = f.get("label", "Audio")
        builder.button(
            text=label,
            callback_data=f"audio_quality:{f['format_id']}",
        )
    builder.button(text="Cancel", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def download_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Video", callback_data="dl_type:video")
    builder.button(text="Audio", callback_data="dl_type:audio")
    builder.button(text="Cancel", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="New Download", callback_data="new_download")
    builder.button(text="Help", callback_data="help")
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Cancel", callback_data="cancel")
    return builder.as_markup()
