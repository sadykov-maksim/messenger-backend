from django.utils import timezone

from django.core.validators import RegexValidator
from django.db import models



# Create your models here.
class TelegramUser(models.Model):
    """Пользователь Telegram"""

    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        verbose_name="Telegram ID",
        help_text="Уникальный идентификатор пользователя Telegram",
    )

    username = models.CharField(
        unique=True,
        max_length=255, null=True, blank=True,
        verbose_name="Username",
        help_text="Telegram-имя пользователя"
    )

    first_name = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="Имя",
        help_text="Имя пользователя из Telegram"
    )

    last_name = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="Фамилия",
        help_text="Фамилия пользователя из Telegram")

    photo = models.ImageField(
        upload_to="avatars/",
        null=True, blank=True,
        verbose_name="Аватарка"
    )

    @property
    def display_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.username:
            return f"@{self.username}"
        else:
            return f"UID: {self.telegram_id}"

    class Meta:
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"
        indexes = [
            models.Index(fields=["telegram_id"]),
        ]

    def __str__(self) -> str:
        return self.display_name


class BotSettings(models.Model):
    """Настройки Telegram-бота"""

    name = models.CharField(
        max_length=100,
        default="Main Bot",
        verbose_name="Название конфигурации",
    )

    bot_token = models.CharField(
        max_length=255,
        verbose_name="Токен Telegram-бота",
    )

    admins = models.ManyToManyField(TelegramUser, related_name="bots", blank=True)
    use_redis = models.BooleanField(default=False, help_text="Использовать RedisStorage")

    redis_host = models.CharField(
        max_length=100, blank=True, null=True, help_text="Хост Redis"
    )
    redis_port = models.IntegerField(
        blank=True, null=True, help_text="Порт Redis"
    )
    redis_pass = models.CharField(
        max_length=100, blank=True, null=True, help_text="Пароль Redis"
    )

    other_params = models.TextField(
        blank=True, null=True, help_text="Дополнительные параметры (необязательно)"
    )

    def redis_dsn(self) -> str | None:
        """
        Возвращает DSN для подключения к Redis.
        """
        if not self.redis_host or not self.redis_port:
            return None
        if self.redis_pass:
            return f"redis://:{self.redis_pass}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    channel_url = models.URLField(
        max_length=255,
        default="https://t.me/telegram",
        verbose_name="Ссылка на канал (для кнопки «Подписаться»)",
    )

    channel_id = models.CharField(
        max_length=255,
        default="-1001005640892",
        verbose_name="Идентификатор канала (для проверки подписки)",
        validators=[
            RegexValidator(
                regex=r"^(-100\d+|@?[A-Za-z0-9_]{5,32})$",
                message=(
                    "Укажи -100... (ID канала) или @username/username (5–32 символа, латиница/цифры/_)."
                ),
            )
        ],
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Использовать эту конфигурацию",
        help_text=(
            "Рекомендуется держать активной только одну конфигурацию."
        ),
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
        help_text="Дата и время создания записи.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено",
        help_text="Дата и время последнего изменения записи.",
    )

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()

    @classmethod
    def get_active_token(cls):
        obj = cls.get_active()
        return obj.bot_token if obj else None

    @classmethod
    def get_admin_ids(cls):
        """Sync version для обычного использования через sync_to_async."""
        bot_settings = cls.get_active()
        if not bot_settings or not hasattr(bot_settings, "admins"):
            return []

        return list(bot_settings.admins.values_list("telegram_id", flat=True))

    class Meta:
        verbose_name = "Конфигурация Telegram-бота"
        verbose_name_plural = "Конфигурации Telegram-бота"
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({'активна' if self.is_active else 'выключена'})"


