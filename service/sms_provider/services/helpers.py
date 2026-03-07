from typing import Optional

from sms_provider.choices import SMSBanReason
from sms_provider.models import SMSProviderSettings, SMSBlacklistedPhone, SMSAccessCode


def _get_settings(provider_settings: SMSProviderSettings | None) -> Optional[SMSProviderSettings]:
    """
    Возвращает переданные настройки SMS-провайдера или активные настройки по умолчанию.

    Используется как безопасный хелпер, чтобы в бизнес-логике не проверять None.
    """

    return provider_settings or SMSProviderSettings.get_active()


def _get_active_ban(phone: str) -> Optional[SMSBlacklistedPhone]:
    """
    Проверяет, находится ли номер телефона в активном бане.

    Возвращает объект бана, если номер заблокирован в текущий момент времени,
    иначе возвращает None.
    """

    bl = SMSBlacklistedPhone.objects.filter(phone_number=phone, is_active=True).first()
    if bl and bl.is_banned_now():
        return bl
    return None


def _expire_if_needed(code: SMSAccessCode, settings_obj: SMSProviderSettings | None) -> bool:
    """
    Лениво переводит код доступа из ACTIVE в EXPIRED, если истёк его срок действия.

    Побочные эффекты:
    - обновляет статус кода в БД;
    - при включённой политике автоматически добавляет номер в blacklist.

    Возвращает:
    - True — если код истёк (уже был EXPIRED или был переведён в EXPIRED);
    - False — если код ещё действителен.
    """

    if code.status != SMSAccessCode.Status.ACTIVE:
        return code.status == SMSAccessCode.Status.EXPIRED

    if not code.is_expired():
        return False

    code.status = SMSAccessCode.Status.EXPIRED
    code.save(update_fields=["status"])

    if settings_obj and settings_obj.blacklist_after_expired:
        SMSBlacklistedPhone.ban(
            phone=code.phone_number,
            minutes=settings_obj.blacklist_duration_minutes,
            reason=SMSBanReason.EXPIRED_CODE,
        )
    return True


def _block_other_active_codes(phone: str) -> None:
    """
    Блокирует все активные коды доступа для указанного номера телефона.

    Используется для гарантии, что у одного номера существует
    не более одного ACTIVE кода одновременно.
    """

    SMSAccessCode.objects.filter(
        phone_number=phone,
        status=SMSAccessCode.Status.ACTIVE,
    ).update(status=SMSAccessCode.Status.BLOCKED)