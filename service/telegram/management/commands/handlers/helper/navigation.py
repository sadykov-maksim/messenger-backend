import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from ...keyboards.inline import main_menu_keyboard
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)



async def show_navigation(chat_input):
    """
    Отображение главного меню пользователю.
    """

    text = "👋 Добро пожаловать в главное меню!\n\nВыбери, с чего начнём 👇"

    if isinstance(chat_input, CallbackQuery):
        try:
            await chat_input.message.edit_text(
                text=text,
                reply_markup=main_menu_keyboard()
            )
        except TelegramBadRequest:
            await chat_input.message.delete()
            await chat_input.message.answer(
                text=text,
                reply_markup=main_menu_keyboard()
            )
        finally:
            await chat_input.answer()
    else:
        await chat_input.answer(
            text=text,
            reply_markup=main_menu_keyboard()
        )

