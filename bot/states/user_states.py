from aiogram.fsm.state import State, StatesGroup


class DownloadStates(StatesGroup):
    waiting_for_link = State()
    processing_link = State()
    choosing_quality = State()
    downloading = State()
