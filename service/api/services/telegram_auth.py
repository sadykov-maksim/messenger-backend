import hashlib
import hmac
import logging
import json
from datetime import datetime, timedelta

import jwt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny

from telegram.models import BotSettings, TelegramUser
from django.conf import settings
from api.utils.init_data import parse_init_data


def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """
    Проверяет подлинность Telegram Login Widget данных.
    """
    data_copy = data.copy()
    check_hash = data_copy.pop("hash", None)

    if check_hash is None:
        logging.error("Поле 'hash' отсутствует в полученных данных.")
        return False

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data_copy.items())
    )

    secret_key = hmac.new(
        "WebAppData".encode(),
        bot_token.encode(),
        hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return calculated_hash == check_hash


def generate_tokens(user):
    """
    Генерирует JWT access и refresh токены для пользователя.
    Время жизни берется из настроек .env / settings.py
    """
    access_payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_MINUTES),
        "type": "access",
    }

    refresh_payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(days=settings.WT_REFRESH_TOKEN_DAYS),
        "type": "refresh",
    }

    access_token = jwt.encode(
        access_payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    refresh_token = jwt.encode(
        refresh_payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return access_token, refresh_token


class TelegramAuthView(APIView):
    permission_classes = [AllowAny]

    ERROR_CODES = {
        "MISSING_HEADER": "AUTH_HEADER_MISSING",
        "INVALID_HEADER_FORMAT": "AUTH_HEADER_INVALID_FORMAT",
        "EMPTY_INIT_DATA": "TELEGRAM_INIT_DATA_EMPTY",
        "INVALID_TELEGRAM_AUTH": "TELEGRAM_AUTH_FAILED",
        "MISSING_USER_DATA": "TELEGRAM_MISSING_USER_DATA",
        "INVALID_DATA_FORMAT": "TELEGRAM_INVALID_DATA_FORMAT",
        "USER_NOT_FOUND": "AUTH_USER_NOT_FOUND",
    }

    def post(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return Response(
                {"code": self.ERROR_CODES["MISSING_HEADER"],
                 "detail": "Missing Authorization header"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not auth_header.startswith("tma "):
            return Response(
                {"code": self.ERROR_CODES["INVALID_HEADER_FORMAT"],
                 "detail": "Invalid Authorization header format. Expected 'tma ...'"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        init_data_raw = auth_header[len("tma "):].strip()
        if not init_data_raw:
            return Response(
                {"code": self.ERROR_CODES["EMPTY_INIT_DATA"],
                 "detail": "Empty Telegram initialization data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logging.warning(f"init_data: {init_data_raw}")
        data = parse_init_data(init_data_raw)

        try:
            bot = BotSettings.objects.filter(is_active=True).first()
            if not bot:
                logging.error("BotSettings not found or not active.")
                raise Exception("Bot settings error")

            if not verify_telegram_auth(data, bot_token=bot.bot_token):
                return Response(
                    {"code": self.ERROR_CODES["INVALID_TELEGRAM_AUTH"],
                     "detail": "Invalid Telegram authentication signature"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            return Response(
                {"code": self.ERROR_CODES["INVALID_TELEGRAM_AUTH"],
                 "detail": "Authentication validation failed (server issue or invalid signature)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "user" not in data or not data["user"]:
            return Response(
                {"code": self.ERROR_CODES["MISSING_USER_DATA"],
                 "detail": "User data not found in Telegram init_data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            telegram_data = json.loads(data["user"])
            telegram_id = int(telegram_data.get("id"))

            user = TelegramUser.objects.filter(telegram_id=telegram_id).first()

            if user is None:
                return Response(
                    {"code": self.ERROR_CODES["USER_NOT_FOUND"],
                     "detail": "User is authenticated via Telegram but not found in the application database."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        except (KeyError, ValueError, TypeError) as e:
            return Response(
                {"code": self.ERROR_CODES["INVALID_DATA_FORMAT"],
                 "detail": f"Invalid format for Telegram user data: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Используем SimpleJWT для токенов
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response_data = {
            "access": str(access),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": f"{user.first_name} {user.last_name}",
                "username": user.username,
                "completed": user.registration_completed,
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
            path=settings.JWT_AUTH_COOKIE_PATH
        )

        return response
