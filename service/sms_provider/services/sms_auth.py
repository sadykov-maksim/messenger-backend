from __future__ import annotations

import hmac as _hmac

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from sms_provider.choices import SMSBanReason
from sms_provider.dto.sms_results import RequestCodeResult, VerifyCodeResult, SendSMSResult
from sms_provider.utils import normalize_phone
from .helpers import _get_settings, _get_active_ban, _block_other_active_codes, \
    _expire_if_needed

from sms_provider.services.sender import send_sms

from sms_provider.models import SMSProviderSettings, SMSAccessCode, SMSBlacklistedPhone


class SMSAuthService:
    """
    SMSAuthService
    """

    @staticmethod
    def ban_phone(phone: str, *, minutes: int, reason: SMSBanReason) -> SMSBlacklistedPhone:
        return SMSBlacklistedPhone.ban(phone=phone, minutes=minutes, reason=reason)

    @staticmethod
    def unblock_phone(phone: str) -> None:
        phone = normalize_phone(phone)
        SMSBlacklistedPhone.objects.filter(phone_number=phone, is_active=True).update(is_active=False)

    @staticmethod
    def request_code(
        phone: str,
        *,
        provider_settings: SMSProviderSettings | None = None,
        message_template: str = "{code}",
    ) -> RequestCodeResult:
        """
        Правила:
        - если телефон забанен -> отказ
        - новый код не чаще чем раз в resend_cooldown_seconds
        - не больше max_sends_per_day за последние 24 часа
        - если превысил лимит -> бан на ban_minutes_after_daily_limit
        - перед созданием нового кода блокируем все ACTIVE предыдущие
        - send_sms вызывается ВНЕ транзакции, чтобы не держать соединение
          во время HTTP-запроса и не откатить сохранённый код при сетевой ошибке
        """

        phone = normalize_phone(phone)
        settings_obj = _get_settings(provider_settings)

        if not settings_obj:
            return RequestCodeResult(ok=False, phone=phone, error="No active SMSProviderSettings")

        black_list = _get_active_ban(phone)
        if black_list:
            return RequestCodeResult(
                ok=False,
                phone=phone,
                banned_until=black_list.banned_until,
                provider=settings_obj.provider,
                error="phone_banned",
            )

        cooldown = int(settings_obj.resend_cooldown_seconds)
        max_per_day = int(settings_obj.max_sends_per_day)
        ban_minutes = int(settings_obj.ban_minutes_after_daily_limit)

        with transaction.atomic():
            now = timezone.now()

            last = (SMSAccessCode.objects.select_for_update().filter(phone_number=phone).order_by("-created_at").first())
            if last:
                passed = (now - last.created_at).total_seconds()
                if passed < cooldown:
                    left = max(0, int(cooldown - passed))
                    return RequestCodeResult(
                        ok=False,
                        phone=phone,
                        cooldown_seconds_left=left,
                        provider=settings_obj.provider,
                        error="cooldown",
                    )

            since = now - timedelta(hours=24)
            cnt = SMSAccessCode.objects.filter(phone_number=phone, created_at__gte=since).count()
            daily_left = max(0, max_per_day - cnt)

            if cnt >= max_per_day:
                ban_obj = SMSBlacklistedPhone.ban(
                    phone=phone,
                    minutes=ban_minutes,
                    reason=SMSBanReason.TOO_MANY_REQUESTS,
                )
                return RequestCodeResult(
                    ok=False,
                    phone=phone,
                    banned_until=ban_obj.banned_until,
                    provider=settings_obj.provider,
                    error="daily_limit",
                )

            _block_other_active_codes(phone)
            code_obj, plain_code = SMSAccessCode.generate_for_phone(phone, provider=settings_obj)

        text = message_template.format(code=plain_code)
        send_res: SendSMSResult = send_sms(phone, text, provider_settings=settings_obj)

        if not send_res.ok:
            SMSAccessCode.objects.filter(pk=code_obj.pk).update(status=SMSAccessCode.Status.BLOCKED)
            return RequestCodeResult(
                ok=False,
                phone=phone,
                provider=settings_obj.provider,
                daily_limit_left=max(0, daily_left - 1),
                error=f"sms_send_failed: {send_res.error}",
                code_id=code_obj.pk,
            )

        return RequestCodeResult(
            ok=True,
            phone=phone,
            provider=settings_obj.provider,
            daily_limit_left=max(0, daily_left - 1),
            code_id=code_obj.pk,
        )

    @staticmethod
    def verify_code(phone: str,code: str,*,provider_settings: SMSProviderSettings | None = None) -> VerifyCodeResult:
        """
        Проверка:
        - если телефон забанен -> отказ
        - берём самый свежий ACTIVE код
        - если протух -> EXPIRED (+ опциональный бан) и отказ
        - если hash не совпал -> attempts++, при превышении -> BLOCKED и отказ
        - если совпал -> USED
        """

        phone = normalize_phone(phone)
        settings_obj = _get_settings(provider_settings)

        bl = _get_active_ban(phone)
        if bl:
            return VerifyCodeResult(
                ok=False,
                phone=phone,
                status="banned",
                banned_until=bl.banned_until,
                error="phone_banned",
            )

        with transaction.atomic():
            obj = (
                SMSAccessCode.objects
                .select_for_update()
                .filter(phone_number=phone, status=SMSAccessCode.Status.ACTIVE)
                .order_by("-created_at")
                .first()
            )

            if not obj:
                return VerifyCodeResult(
                    ok=False,
                    phone=phone,
                    status="no_active_code",
                    error="no_active_code",
                )

            if _expire_if_needed(obj, settings_obj):
                return VerifyCodeResult(
                    ok=False,
                    phone=phone,
                    status="expired",
                    error="expired",
                )

            if not _hmac.compare_digest(obj.code_hash, SMSAccessCode.hash_code(code)):
                obj.verify_attempts += 1

                if obj.verify_attempts >= obj.max_attempts:
                    obj.status = SMSAccessCode.Status.BLOCKED
                    obj.save(update_fields=["verify_attempts", "status"])
                    return VerifyCodeResult(
                        ok=False,
                        phone=phone,
                        status="blocked",
                        attempts_left=0,
                        error="too_many_attempts",
                    )

                obj.save(update_fields=["verify_attempts"])
                left = max(0, obj.max_attempts - obj.verify_attempts)
                return VerifyCodeResult(
                    ok=False,
                    phone=phone,
                    status="invalid_code",
                    attempts_left=left,
                    error="invalid_code",
                )

            obj.status = SMSAccessCode.Status.USED
            obj.used_at = timezone.now()
            obj.save(update_fields=["status", "used_at"])

            return VerifyCodeResult(ok=True, phone=phone, status="used", attempts_left=0)