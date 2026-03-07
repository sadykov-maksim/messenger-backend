from asgiref.sync import sync_to_async
from aiogram.filters import BaseFilter
from aiogram.types import Message
from telegram.models import BotSettings


class AdminFilter(BaseFilter):
    is_admin: bool = True

    async def __call__(self, message: Message) -> bool:
        admin_ids = await sync_to_async(BotSettings.get_admin_ids)()
        return (message.from_user.id in admin_ids) == self.is_admin