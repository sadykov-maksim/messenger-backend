from aiogram import types, Router, F, Bot
import logging
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode

from asgiref.sync import sync_to_async

from telegram.management.commands.keyboards.inline import mistakes_keyboard

echo_router = Router()

logger = logging.getLogger(__name__)


@echo_router.message(F.text, StateFilter(None))
async def unknown_command_handler(message: types.Message):
   text = (
       "😅 <b>Ой-ой! Такой команды не нашлось...</b>.\n\n"
       "💡 <i>Попробуйте воспользоваться клавиатурой.</i>"
   )

   await message.answer(text, parse_mode="HTML", reply_markup=mistakes_keyboard())


@echo_router.message(F.text)
async def bot_echo_all(message: types.Message, state: FSMContext, bot: Bot):
   state_name = await state.get_state()
   text = (
       "😅 <b>Ой-ой! Такой команды не нашлось...</b>.\n\n"
       "💡 <i>Попробуйте воспользоваться клавиатурой.</i>"
   )

   await message.answer(text, parse_mode="HTML", reply_markup=mistakes_keyboard())


