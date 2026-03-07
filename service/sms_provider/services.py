from typing import Any

from django.utils import timezone

from sms_provider.types import SendSMSResult
from sms_provider.clients.custom_http import CustomHttpSMSClient
from sms_provider.clients.smsru import SMSRuClient

from .models import SMSProviderSettings
from .utils import normalize_phone


def get_client(settings_obj: SMSProviderSettings):
    provider = settings_obj.provider

    if provider == SMSProviderSettings.Provider.CUSTOM_HTTP:
        if not settings_obj.api_base_url:
            raise ValueError("SMSProviderSettings.api_base_url is required for custom_http")
        return CustomHttpSMSClient(
            base_url=settings_obj.api_base_url,
            api_key=settings_obj.api_key,
            sender_id=settings_obj.sender_id,
        )

    if provider == SMSProviderSettings.Provider.SMSRU:
        if not settings_obj.api_key:
            raise ValueError("SMSProviderSettings.api_key is required for SMS.ru (api_id)")
        return SMSRuClient(
            api_id=settings_obj.api_key,
            sender=settings_obj.sender_id,
        )

    raise ValueError(f"Unsupported SMS provider: {provider}")


def send_sms(phone: str, text: str, *, provider_settings: SMSProviderSettings | None = None, **kwargs: Any) -> SendSMSResult:
    phone = normalize_phone(phone)

    settings_obj = provider_settings or SMSProviderSettings.get_active()
    if not settings_obj:
        return SendSMSResult(ok=False, provider="none", error="No active SMSProviderSettings")

    try:
        client = get_client(settings_obj)
    except Exception as e:
        return SendSMSResult(ok=False, provider=settings_obj.provider, error=f"Provider client init error: {e}")

    result = client.send_sms(phone, text, **kwargs)

    return result