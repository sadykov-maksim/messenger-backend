
import logging
from typing import Optional

from asgiref.sync import sync_to_async

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

#from telegram.management.commands.date_access import get_user_by_ref_code
from telegram.models import BotSettings, TelegramUser



logger = logging.getLogger(__name__)


async def get_or_create_user(event, ref_code: str = None):
    """
    Получает существующего пользователя или создаёт нового на основе данных Telegram события.
    """

    current_user = event.from_user

    # Get the referrer if the code is passed
    referrer = None
    #if ref_code:
    #    referrer = await get_user_by_ref_code(ref_code)

    # Creating or receiving a user
    existing_user, created = await sync_to_async(TelegramUser.objects.get_or_create)(
        telegram_id=current_user.id,
        defaults={
            "username": current_user.username,
            "first_name": current_user.first_name or "",
            "last_name": current_user.last_name or "",
        }
    )
    return existing_user, created

@sync_to_async
def get_user_with_region(telegram_id: int):
    return (
        TelegramUser.objects
        .get(user_id=telegram_id)
    )


async def change_consent_status(event, status: bool = False) -> bool:
    """
    Безопасно обновляет статус согласия.
    Возвращает True при успешном обновлении, иначе False.
    """

    try:
        updated_count = await TelegramUser.objects.filter(telegram_id=event).aupdate(consent_accepted=status)
        return bool(updated_count)
    except DatabaseError as e:
        logger.error(f"Ошибка БД при обновлении статуса для {event.from_user.id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка: {e}")
        return False

async def change_finish_status(event, status: bool = False) -> bool:
    """
    Безопасно обновляет статус согласия.
    Возвращает True при успешном обновлении, иначе False.
    """

    try:
        updated_count = await TelegramUser.objects.filter(telegram_id=event).aupdate(registration_completed=status)
        return bool(updated_count)
    except DatabaseError as e:
        logger.error(f"Ошибка БД при обновлении статуса для {event.from_user.id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка: {e}")
        return False


async def get_current_user(event):
    """
    Возвращает текущего пользователя Telegram или None, если он не найден.
    """

    current_user = event.from_user

    try:
        return await sync_to_async(TelegramUser.objects.get)(
            telegram_id=current_user.id
        )
    except TelegramUser.DoesNotExist:
        logger.info(f"Пользователь с telegram_id={current_user.id} не найден")
        return None


@sync_to_async
def save_user(user: TelegramUser, update_fields: list[str] | None = None):
    """
    Асинхронно сохраняет изменения пользователя в базе данных.
    """

    user.save(update_fields=update_fields)



@sync_to_async
def get_active_channel() -> Optional[str]:
    obj = BotSettings.objects.filter(is_active=True).first()
    return obj if obj else None
