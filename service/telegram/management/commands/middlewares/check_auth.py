from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from asgiref.sync import sync_to_async

from telegram.management.commands.date_access.user import get_current_user

import logging
logger = logging.getLogger(__name__)
from telegram.models import TelegramUser


class CheckUserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.text:
            if event.text.startswith("/start"):
                return await handler(event, data)

        user_id = event.from_user.id
        user = await self.get_user(user_id)

        if user is None:
            await event.answer("Вы не зарегистрированы! Используйте /start.", show_alert=True)
            return

        data["user"] = user

        return await handler(event, data)

    async def get_user(self, user_id: int) -> TelegramUser | None:
        try:
            return await sync_to_async(TelegramUser.objects.get)(telegram_id=user_id)
        except TelegramUser.DoesNotExist:
            logger.info(f"Пользователь с telegram_id={user_id} не найден")
            return None