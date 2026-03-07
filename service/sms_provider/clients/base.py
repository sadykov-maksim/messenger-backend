from abc import ABC, abstractmethod
from typing import Any

from sms_provider.types import SendSMSResult


class BaseSMSClient(ABC):
    @abstractmethod
    def send_sms(self, phone: str, text: str, **kwargs: Any) -> SendSMSResult:
        raise NotImplementedError