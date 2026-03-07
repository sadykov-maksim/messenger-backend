from asgiref.sync import sync_to_async

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError



async def is_user_subscribed(bot: Bot, channel_id: str | int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return False

    return member.status in ("member", "administrator", "creator")