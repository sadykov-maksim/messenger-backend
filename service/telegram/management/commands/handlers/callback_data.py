from enum import IntEnum, auto, Enum
from aiogram.filters.callback_data import CallbackData


class MenuActions(IntEnum):
    home = auto()
    help = auto()
    root = auto()


class MenuCbData(CallbackData, prefix="main_menu"):
    action: MenuActions

