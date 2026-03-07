from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .choices import SMSBanReason
from .models import SMSAccessCode, SMSBlacklistedPhone, SMSProviderSettings


@shared_task(bind=True, ignore_result=True)
def expire_sms_codes(self) -> int:
    """
    Переводит протухшие ACTIVE коды в EXPIRED.
    Если включено blacklist_after_expired — банит телефон.
    Возвращает кол-во помеченных кодов.
    """
    now = timezone.now()
    settings_obj = SMSProviderSettings.get_active()

    # Найдём id протухших активных кодов (ограничим пачкой, чтобы не грузить БД)
    qs = (
        SMSAccessCode.objects
        .filter(status=SMSAccessCode.Status.ACTIVE, expires_at__lte=now)
        .only("id", "phone_number")
        .order_by("id")
    )

    ids = list(qs.values_list("id", flat=True)[:5000])  # batch
    if not ids:
        return 0

    with transaction.atomic():
        # 1) помечаем как EXPIRED
        SMSAccessCode.objects.filter(id__in=ids).update(status=SMSAccessCode.Status.EXPIRED)

        # 2) опционально — баним телефоны
        if settings_obj and settings_obj.blacklist_after_expired:
            phones = list(
                SMSAccessCode.objects.filter(id__in=ids).values_list("phone_number", flat=True).distinct()
            )
            minutes = settings_obj.blacklist_duration_minutes

            # upsert бана (update_or_create на каждый телефон — ok при небольшом числе, иначе bulk)
            for p in phones:
                SMSBlacklistedPhone.ban(
                    phone=p,
                    minutes=minutes,
                    reason=SMSBanReason.EXPIRED_CODE,
                )

    return len(ids)