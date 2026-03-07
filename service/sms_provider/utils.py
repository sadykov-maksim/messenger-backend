import re
from django.core.validators import RegexValidator

PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+\d{9,15}$",
    message="Телефон должен быть в формате +79991234567",
)

def normalize_phone(phone: str) -> str:
    """
    Приводит телефон к формату E.164 (+79991234567).
    Возвращает пустую строку, если номер некорректен.
    """

    phone = (phone or "").strip()

    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("8") and len(phone) == 11:
        phone = "+7" + phone[1:]

    if phone.startswith("7") and len(phone) == 11:
        phone = "+7" + phone

    if not phone.startswith("+"):
        return ""

    if not re.fullmatch(r"\+\d{9,15}", phone):
        return ""

    return phone

def normalize_phone_or_raise(phone: str) -> str:
    phone = normalize_phone(phone)
    if not phone:
        raise ValueError("Invalid phone number")
    return phone