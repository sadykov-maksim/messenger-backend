from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.contrib.auth import get_user_model


class TelegramUserManager(BaseUserManager):
    def create_user(self, username=None, telegram_id=None, **extra_fields):
        if not telegram_id and not extra_fields.get("is_superuser"):
            last_id = self.model.objects.filter(telegram_id__lt=0).aggregate(models.Min('telegram_id'))[
                'telegram_id__min']

            if last_id is None:
                telegram_id = -1000000  # Начальная точка для "не-телеграм" пользователей
            else:
                telegram_id = last_id - 1
            #raise ValueError("Telegram ID is required")

        if not username:
            username = f"anonymous_{telegram_id}"

        user = self.model(username=username, telegram_id=telegram_id, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.ADMIN)

        return self.create_user(
            username=username,
            telegram_id=1,
            **extra_fields
        )