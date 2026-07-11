from aiogram import Router
from aiogram.types import ErrorEvent
from loguru import logger

from bot.keyboards.inline import main_menu_keyboard

router = Router()


@router.errors()
async def error_handler(event: ErrorEvent) -> bool:
    logger.error(f"Update error: {event.exception}")
    logger.exception(event.exception)

    if event.update.message:
        await event.update.message.answer(
            "An unexpected error occurred. Please try again.",
            reply_markup=main_menu_keyboard(),
        )
    elif event.update.callback_query:
        await event.update.callback_query.message.edit_text(
            "An unexpected error occurred. Please try again.",
            reply_markup=main_menu_keyboard(),
        )

    return True
