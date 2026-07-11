from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import main_menu_keyboard
from bot.states.user_states import DownloadStates

router = Router()


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (
        "<b>Welcome to Downloader Bot!</b>\n\n"
        "I can download videos and audio from:\n"
        "• YouTube (videos, shorts, audio)\n"
        "• Instagram (posts, reels, stories)\n\n"
        "Send me a link to get started!"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def help_command(message: Message, state: FSMContext) -> None:
    text = (
        "<b>How to use:</b>\n\n"
        "1. Send a YouTube or Instagram link\n"
        "2. Choose Video or Audio\n"
        "3. Select your preferred quality\n"
        "4. Wait for the download\n\n"
        "<b>Supported platforms:</b>\n"
        "• YouTube: videos, shorts, audio\n"
        "• Instagram: posts, reels, stories\n\n"
        "<b>Commands:</b>\n"
        "/start - Restart the bot\n"
        "/help - Show this message\n"
        "/cancel - Cancel current operation\n"
        "/cookies - Upload Instagram cookies for downloads"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Operation cancelled.", reply_markup=main_menu_keyboard())


@router.callback_query(lambda c: c.data == "help")
async def help_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    text = (
        "<b>How to use:</b>\n\n"
        "1. Send a YouTube or Instagram link\n"
        "2. Choose Video or Audio\n"
        "3. Select your preferred quality\n"
        "4. Wait for the download\n\n"
        "<b>Supported platforms:</b>\n"
        "• YouTube: videos, shorts, audio\n"
        "• Instagram: posts, reels, stories"
    )
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())


@router.callback_query(lambda c: c.data == "new_download")
async def new_download_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(DownloadStates.waiting_for_link)
    await callback.message.edit_text(
        "Send me the link you want to download:"
    )


@router.callback_query(lambda c: c.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Cancelled")
    await state.clear()
    await callback.message.edit_text(
        "Operation cancelled.",
        reply_markup=main_menu_keyboard(),
    )
