import re

from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from sms_provider.services.sms_auth import SMSAuthService
from sms_provider.utils import normalize_phone


class SMSRequestCodeView(APIView):
    """
    POST /auth/sms/request/
    Body: { "phone": "+79991234567" }
    """
    permission_classes = [AllowAny]

    ERROR_CODES = {
        "MISSING_PHONE": "SMS_PHONE_MISSING",
        "INVALID_PHONE": "SMS_PHONE_INVALID",
        "PHONE_BANNED": "SMS_PHONE_BANNED",
        "COOLDOWN": "SMS_COOLDOWN",
        "DAILY_LIMIT": "SMS_DAILY_LIMIT",
        "SEND_FAILED": "SMS_SEND_FAILED",
        "NO_SETTINGS": "SMS_NO_SETTINGS",
        "USER_NOT_FOUND": "SMS_USER_NOT_FOUND",
    }

    def post(self, request):
        data = request.data or {}
        phone_raw = data.get("phone") or data.get("phone_number")

        if not phone_raw:
            return Response(
                {"code": self.ERROR_CODES["MISSING_PHONE"], "detail": "Введите номер телефона."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = normalize_phone(str(phone_raw))
        if not phone or len(re.sub(r"[^\d]", "", phone)) < 10:
            return Response(
                {"code": self.ERROR_CODES["INVALID_PHONE"], "detail": "Неверный формат номера телефона. Пример: +7 900 123-45-67"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_user_model()
        if not user.objects.filter(phone_number=phone).exists():
            return Response(
                {"code": self.ERROR_CODES["USER_NOT_FOUND"], "detail": "Пользователь с таким номером не найден."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = SMSAuthService.request_code(phone)

        if result.ok:
            return Response(
                {"detail": "Code sent", "phone": result.phone},
                status=status.HTTP_200_OK,
            )

        error = result.error or ""

        if error == "phone_banned":
            return Response(
                {
                    "code": self.ERROR_CODES["PHONE_BANNED"],
                    "detail": "Ваш номер телефона заблокирован.",
                    "banned_until": result.banned_until,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if error == "cooldown":
            return Response(
                {
                    "code": self.ERROR_CODES["COOLDOWN"],
                    "detail": "Слишком много попыток. Пожалуйста, подождите немного.",
                    "cooldown_seconds_left": result.cooldown_seconds_left,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if error == "daily_limit":
            return Response(
                {
                    "code": self.ERROR_CODES["DAILY_LIMIT"],
                    "detail": "Превышен дневной лимит SMS. Попробуйте завтра.",
                    "banned_until": result.banned_until,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if error == "No active SMSProviderSettings":
            return Response(
                {"code": self.ERROR_CODES["NO_SETTINGS"], "detail": "Отправка SMS временно недоступна. Попробуйте позже."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if error.startswith("sms_send_failed"):
            return Response(
                {"code": self.ERROR_CODES["SEND_FAILED"], "detail": "Не удалось отправить SMS. Проверьте номер телефона и попробуйте ещё раз."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"code": "SMS_UNKNOWN_ERROR", "detail": error},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class SMSVerifyCodeView(APIView):
    """
    POST /auth/sms/verify/
    Body: { "phone": "+79991234567", "code": "123456" }
    Возвращает JWT-токены если код верный.
    """
    permission_classes = [AllowAny]

    ERROR_CODES = {
        "MISSING_PHONE": "SMS_PHONE_MISSING",
        "MISSING_CODE": "SMS_CODE_MISSING",
        "INVALID_PHONE": "SMS_PHONE_INVALID",
        "PHONE_BANNED": "SMS_PHONE_BANNED",
        "NO_ACTIVE_CODE": "SMS_NO_ACTIVE_CODE",
        "EXPIRED": "SMS_CODE_EXPIRED",
        "INVALID_CODE": "SMS_CODE_INVALID",
        "BLOCKED": "SMS_CODE_BLOCKED",
        "USER_NOT_FOUND": "SMS_USER_NOT_FOUND",
    }

    def post(self, request):
        data = request.data or {}
        phone_raw = data.get("phone") or data.get("phone_number")
        code = data.get("code")

        if not phone_raw:
            return Response(
                {"code": self.ERROR_CODES["MISSING_PHONE"], "detail": "Missing phone"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not code:
            return Response(
                {"code": self.ERROR_CODES["MISSING_CODE"], "detail": "Missing code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone = normalize_phone(str(phone_raw))
        if not phone or len(re.sub(r"[^\d]", "", phone)) < 10:
            return Response(
                {"code": self.ERROR_CODES["INVALID_PHONE"], "detail": "Invalid phone format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = SMSAuthService.verify_code(phone, str(code))

        if not result.ok:
            error = result.error or ""

            if error == "phone_banned":
                return Response(
                    {
                        "code": self.ERROR_CODES["PHONE_BANNED"],
                        "detail": "Phone is banned",
                        "banned_until": result.banned_until,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if error == "no_active_code":
                return Response(
                    {"code": self.ERROR_CODES["NO_ACTIVE_CODE"], "detail": "No active code found, request a new one"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if error == "expired":
                return Response(
                    {"code": self.ERROR_CODES["EXPIRED"], "detail": "Code has expired, request a new one"},
                    status=status.HTTP_410_GONE,
                )

            if error == "invalid_code":
                return Response(
                    {
                        "code": self.ERROR_CODES["INVALID_CODE"],
                        "detail": "Invalid code",
                        "attempts_left": result.attempts_left,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if error == "too_many_attempts":
                return Response(
                    {
                        "code": self.ERROR_CODES["BLOCKED"],
                        "detail": "Too many invalid attempts, request a new code",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            return Response(
                {"code": "SMS_UNKNOWN_ERROR", "detail": error},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Код верный — ищем пользователя и выдаём токены
        User = get_user_model()
        user = User.objects.filter(phone_number=phone).first()

        if user is None:
            return Response(
                {"code": self.ERROR_CODES["USER_NOT_FOUND"], "detail": "User with this phone not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return _make_jwt_response(user, phone)


def _make_jwt_response(user, phone: str) -> Response:
    """Общий хелпер для выдачи JWT-токенов и установки refresh-куки."""

    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    response_data = {
        "access": str(access),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "phone": getattr(user, "phone_number", phone),
            "first_name": getattr(user, "first_name", "") or "",
            "last_name": getattr(user, "last_name", "") or "",
            "display_name": (
                f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            ) or getattr(user, "username", "") or phone,
            "username": getattr(user, "username", "") or "",
            "completed": getattr(user, "registration_completed", True),
        },
    }

    response = Response(response_data, status=status.HTTP_200_OK)

    cookie_max_age = settings.JWT_REFRESH_TOKEN_DAYS * 24 * 3600
    response.set_cookie(
        key=settings.JWT_AUTH_COOKIE_REFRESH,
        value=str(refresh),
        domain=settings.JWT_AUTH_COOKIE_DOMAIN,
        max_age=cookie_max_age,
        httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        path=settings.JWT_AUTH_COOKIE_PATH,
    )

    return response