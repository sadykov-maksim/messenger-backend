import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django_cryptography.fields import encrypt
from django.db.models import Q
from django.utils import timezone

from sms_provider.choices import SMSBanReason
from sms_provider.utils import PHONE_VALIDATOR, normalize_phone_or_raise


# Create your models here.
class SMSProviderSettings(models.Model):
    """
    Настройки SMS провайдера.
    """

    class Provider(models.TextChoices):
        SMSC = "smsc", "SMSC.ru"

    name = models.CharField(
        max_length=100,
        default="Main SMS Provider",
        verbose_name="Название настройки",
    )

    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        default=Provider.SMSC,
        verbose_name = "SMS-провайдер",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активная настройка",
        help_text="Должна быть активна только одна запись",
    )

    login = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Логин",
        help_text="Логин для авторизации у SMS-провайдера",
    )

    password = encrypt(models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Пароль",
        help_text="Пароль или API-ключ для авторизации у SMS-провайдера",
    ))

    sender_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Имя отправителя",
        help_text="Имя/подпись отправителя (если поддерживается провайдером)",
    )

    # codes policy
    code_ttl_minutes = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(1)],
        verbose_name = "Время жизни кода (мин)",
    )
    code_length = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(4)],
        verbose_name = "Длина SMS-кода",
    )
    max_verify_attempts = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name="Максимум попыток ввода кода",
    )

    # rate limit
    resend_cooldown_seconds = models.PositiveIntegerField(
        default=90,
        validators=[MinValueValidator(1)],
        verbose_name="Интервал повторной отправки (сек)",
        help_text="Минимальный интервал между запросами кода для одного телефона",
    )

    # daily limit
    max_sends_per_day = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name="Лимит SMS в сутки",
        help_text="Сколько раз можно запросить SMS за 24 часа на один телефон",
    )

    ban_minutes_after_daily_limit = models.PositiveIntegerField(
        default=24 * 60,
        validators=[MinValueValidator(1)],
        verbose_name="Бан при превышении лимита (мин)",
        help_text="На сколько минут банить номер при превышении суточного лимита",
    )

    blacklist_after_expired = models.BooleanField(
        default=True,
        verbose_name="Банить при истечении кода",
        help_text="Если включено — номер попадёт в blacklist, если код истёк и не был использован",

    )
    blacklist_duration_minutes = models.PositiveIntegerField(
        default=24 * 60,
        validators=[MinValueValidator(0)],
        verbose_name="Длительность бана (мин)",
        help_text="На сколько минут банить номер (0 — навсегда)",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    @classmethod
    def get_active(cls) -> "SMSProviderSettings | None":
        return cls.objects.filter(is_active=True).order_by("-updated_at").first()

    def __str__(self) -> str:
        active = " [active]" if self.is_active else ""
        return f"{self.name} ({self.get_provider_display()}){active}"

    class Meta:
        verbose_name = "Настройка SMS провайдера"
        verbose_name_plural = "Настройки SMS провайдеров"
        indexes = [models.Index(fields=["is_active", "provider"])]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="only_one_active_sms_provider_settings",
            )
        ]


class SMSBlacklistedPhone(models.Model):
    """
    Заблокированный номер телефона
    """

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[PHONE_VALIDATOR],
        verbose_name="Номер телефона",
        help_text="Номер телефона в нормализованном формате",
    )

    reason = models.CharField(
        max_length=32,
        choices=SMSBanReason.choices,
        default=SMSBanReason.EXPIRED_CODE,
        verbose_name="Причина блокировки",
        help_text="Причина, по которой номер был заблокирован",
    )

    banned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата блокировки",
        help_text="Дата и время применения блокировки",
    )

    banned_until = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Блокировка действует до",
        help_text="Если не указано — блокировка бессрочная",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Активная блокировка",
        help_text="Определяет, действует ли блокировка в данный момент",
    )

    def is_banned_now(self) -> bool:
        if not self.is_active:
            return False
        if self.banned_until is None:
            return True
        now = timezone.now()
        return now < self.banned_until

    @classmethod
    def ban(cls, phone: str, minutes: int = 60, reason: str = SMSBanReason.EXPIRED_CODE) -> "SMSBlacklistedPhone":
        phone = normalize_phone_or_raise(phone)

        if minutes < 0:
            raise ValueError("minutes must be >= 0")

        now = timezone.now()
        until = None if minutes == 0 else now + timedelta(minutes=minutes)

        obj, _ = cls.objects.update_or_create(
            phone_number=phone,
            defaults={
                "reason": reason,
                "banned_at": now,
                "banned_until": until,
                "is_active": True,
            },
        )
        return obj

    class Meta:
        verbose_name = "Телефон в чёрном списке"
        verbose_name_plural = "Чёрный список телефонов"
        indexes = [
            models.Index(fields=["phone_number", "is_active"]),
            models.Index(fields=["is_active", "banned_until"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone_number} ({self.get_reason_display()})"


class SMSAccessCode(models.Model):
    """
    Хранит коды доступа/верификации.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        USED = "used", "Использован"
        EXPIRED = "expired", "Истёк"
        BLOCKED = "blocked", "Заблокирован"

    phone_number = models.CharField(
        max_length=20,
        validators=[PHONE_VALIDATOR],
        db_index=True,
        verbose_name="Номер телефона",
        help_text="Номер телефона в нормализованном формате",
    )

    code_hash = models.CharField(
        max_length=64,
        db_index=True,
        verbose_name="Хеш кода",
        help_text="HMAC-SHA256 от кода (сам код не хранится)",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name="Статус",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Дата создания",
    )

    expires_at = models.DateTimeField(
        db_index=True,
        verbose_name="Действителен до",
        help_text="Дата и время окончания действия кода",
    )

    verify_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Попыток ввода",
    )

    max_attempts = models.PositiveIntegerField(
        default=5,
        verbose_name="Максимум попыток",
    )

    used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата использования",
    )

    provider = models.ForeignKey(
        SMSProviderSettings,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="codes",
        verbose_name="Настройка провайдера",
    )

    meta = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Метаданные",
        help_text="Ответ провайдера, message_id и т.п.",
    )

    @staticmethod
    def hash_code(code: str) -> str:
        return hmac.new(
            key=settings.SECRET_KEY.encode("utf-8"),
            msg=code.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    @classmethod
    def generate_for_phone(cls,phone: str,provider: SMSProviderSettings | None = None) -> tuple["SMSAccessCode", str]:
        phone = normalize_phone_or_raise(phone)

        provider = provider or SMSProviderSettings.get_active()
        ttl = provider.code_ttl_minutes if provider else 15
        length = provider.code_length if provider else 6
        max_attempts = provider.max_verify_attempts if provider else 5

        plain_code = str(secrets.randbelow(10**length)).zfill(length)

        obj = cls.objects.create(
            phone_number=phone,
            code_hash=cls.hash_code(plain_code),
            status=cls.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(minutes=ttl),
            max_attempts=max_attempts,
            provider=provider,
        )
        return obj, plain_code

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def mark_used(self):
        if self.status == self.Status.USED:
            return
        self.status = self.Status.USED
        self.used_at = timezone.now()
        self.save(update_fields=["status", "used_at"])

    class Meta:
        verbose_name = "SMS-код доступа"
        verbose_name_plural = "SMS-коды доступа"
        indexes = [
            models.Index(fields=["phone_number", "created_at"]),
            models.Index(fields=["phone_number", "status", "expires_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone_number} [{self.get_status_display()}]"