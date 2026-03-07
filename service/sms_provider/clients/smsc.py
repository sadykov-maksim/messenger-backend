import requests
from sms_provider.dto.sms_results import SendSMSResult


class SMSCClient:
    BASE_URL = "https://smsc.ru/sys/send.php"

    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password

    def send_sms(self, phone: str, text: str, **kwargs) -> SendSMSResult:
        params = {
            "login": self.login,
            "psw": self.password,
            "phones": phone,
            "mes": text,
            "fmt": 3,
            "charset": "utf-8",
        }
        params.update(kwargs)

        response = requests.get(self.BASE_URL, params=params, timeout=10)
        data = response.json()

        if "error" in data:
            return SendSMSResult(ok=False, provider="smsc", error=data["error"], raw=data)

        return SendSMSResult(
            ok=True,
            provider="smsc",
            provider_message_id=str(data.get("id", "")),
            raw=data,
        )
    def send_telegram(self, phone: str, text: str, **kwargs) -> SendSMSResult:
        return self.send_sms(phone, text, tg=1, **kwargs)