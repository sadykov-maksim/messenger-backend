import requests
from typing import Any

from sms_provider.types import SendSMSResult


class SMSRuClient:
    def __init__(self, api_id: str, sender: str | None = None, timeout: int = 10):
        self.api_id = api_id
        self.sender = sender
        self.timeout = timeout

    def send_sms(self, phone: str, text: str, **kwargs: Any) -> SendSMSResult:
        url = "https://sms.ru/sms/send"
        data = {
            "api_id": self.api_id,
            "to": phone,
            "msg": text,
            "json": 1,
        }
        if self.sender:
            data["from"] = self.sender

        try:
            r = requests.post(url, data=data, timeout=self.timeout)
            if r.status_code >= 400:
                return SendSMSResult(
                    ok=False,
                    provider="smsru",
                    raw={"status_code": r.status_code, "text": r.text},
                    error=f"HTTP {r.status_code}",
                )

            resp = r.json()
            # Успех у sms.ru обычно: status == "OK"
            ok = resp.get("status") == "OK"
            # message_id может лежать в resp["sms"][phone]["sms_id"]
            message_id = None
            sms_block = (resp.get("sms") or {}).get(phone) or {}
            message_id = sms_block.get("sms_id")

            return SendSMSResult(
                ok=ok,
                provider="smsru",
                provider_message_id=message_id,
                raw=resp,
                error=None if ok else (resp.get("status_text") or "send failed"),
            )
        except Exception as e:
            return SendSMSResult(ok=False, provider="smsru", raw=None, error=str(e))