from typing import Any

from sms_provider.dto.sms_results import SendSMSResult

from sms_provider.models import SMSProviderSettings
from sms_provider.utils import normalize_phone
from sms_provider.clients.smsc import SMSCClient


def get_client(settings_obj: SMSProviderSettings):
    provider = settings_obj.provider

    if provider == SMSProviderSettings.Provider.SMSC:
        if not settings_obj.login or not settings_obj.password:
            raise ValueError("SMSProviderSettings.login/password is required for SMSC")

        return SMSCClient(login=settings_obj.login, password=settings_obj.password)

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

    try:
        result = client.send_telegram(phone, text, **kwargs)
    except Exception as e:
        return SendSMSResult(ok=False, provider=settings_obj.provider, error=f"SMS send error: {e}")

    return result