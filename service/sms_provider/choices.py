from django.db import models


class SMSBanReason(models.TextChoices):
    EXPIRED_CODE = "expired_code", "Код истёк"
    TOO_MANY_ATTEMPTS = "too_many_attempts", "Слишком много попыток"
    TOO_MANY_REQUESTS = "too_many_requests", "Слишком много SMS"
    INVALID_CODE = "invalid_code", "Неверный код"
    FRAUD_SUSPECTED = "fraud_suspected", "Подозрение на мошенничество"
    MANUAL = "manual", "Ручная блокировка администратором"
    PROVIDER_ERROR = "provider_error", "Ошибка SMS-провайдера"