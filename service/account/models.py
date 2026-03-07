from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

from django.utils import timezone

from account.managers import AccountManager
from telegram.models import TelegramUser


# Create your models here.
class Language(models.Model):
    """Язык интерфейса пользователя"""

    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Код языка",
        help_text="ISO-код языка (ru, en, es и т.д.)",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="Название",
        help_text="Название языка",
    )

    emoji = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="Эмодзи",
        help_text="Флаг или эмодзи языка",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Доступен для выбора пользователями",
    )

    class Meta:
        verbose_name = "Язык"
        verbose_name_plural = "Языки"
        ordering = ("name",)

    def __str__(self):
        return f"{self.emoji} {self.name}" if self.emoji else self.name


class Region(models.Model):
    """Регион пользователя"""

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Код региона",
        help_text="Уникальный код региона (us, eu, asia и т.д.)",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="Название",
        help_text="Название региона",
    )

    emoji = models.CharField(
        max_length=5,
        blank=True,
        verbose_name="Эмодзи",
        help_text="Флаг или эмодзи региона",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Доступен для выбора пользователями",
    )

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"
        ordering = ("name",)

    def __str__(self):
        return f"{self.emoji} {self.name}" if self.emoji else self.name


class Timezone(models.Model):
    """Часовой пояс пользователя"""

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Название",
        help_text="Название часового пояса (UTC+3, Europe/Moscow и т.д.)",
    )

    offset = models.IntegerField(
        verbose_name="Смещение UTC",
        help_text="Смещение относительно UTC в минутах",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Доступен для выбора пользователями",
    )

    class Meta:
        verbose_name = "Часовой пояс"
        verbose_name_plural = "Часовые пояса"
        ordering = ("offset",)

    def __str__(self):
        sign = "+" if self.offset >= 0 else "-"
        hours = abs(self.offset) // 60
        return f"UTC{sign}{hours}"


class Account(AbstractUser):
    """Account"""

    class Role(models.TextChoices):
        USER = "user", "Пользователь"
        SUPPORT = "support", "Поддержка"
        MANAGER = "manager", "Менеджер"
        ADMIN = "admin", "Администратор"

    objects = AccountManager()

    public_key = models.TextField(null=True, blank=True, verbose_name="Публичный ключ")

    telegram = models.OneToOneField(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="account",
        verbose_name="Telegram аккаунт",
    )

    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        verbose_name="Email",
        help_text="Электронная почта пользователя"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        verbose_name="Роль",
        help_text="Роль пользователя в системе",
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

    phone_number = models.CharField(
        max_length=20, null=True, blank=True,
        validators=[RegexValidator(r'^\+?\d{9,15}$')],
        verbose_name="Телефон",
        help_text="Номер телефона пользователя"
    )

    photo = models.ImageField(
        upload_to="avatars/",
        null=True, blank=True,
        verbose_name="Аватарка",
        help_text="Аватарка пользователя"
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Регион",
    )

    timezone = models.ForeignKey(
        Timezone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Часовой пояс",
    )

    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Язык",
    )

    consent_accepted = models.BooleanField(
        default=False,
        verbose_name="Согласие на обработку ПДн",
        help_text="Пользователь дал согласие на обработку персональных данных"
    )

    registration_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации",
        help_text="Дата и время первого взаимодействия с ботом"
    )

    is_online = models.BooleanField(default=False, verbose_name="Онлайн")

    last_seen = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Последний визит",
    )

    hide_last_seen = models.BooleanField(
        default=False,
        verbose_name="Скрыть время последнего визита",
    )

    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя активность",
        help_text="Дата и время последнего действия пользователя"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def avatar(self):
        if self.photo:
            return self.photo
        if self.telegram and self.telegram.photo:
            return self.telegram.photo
        return None

    @property
    def display_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return f"{self.email}"

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    @property
    def is_support(self) -> bool:
        return self.role == self.Role.SUPPORT

    class Meta:
        verbose_name = "Аккаунт"
        verbose_name_plural = "Аккаунты"
        ordering = ("-registration_date",)
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["region"]),
        ]

    def __str__(self) -> str:
        return self.display_name


class UserLoginHistory(models.Model):
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="login_history",
        verbose_name="Пользователь"
    )
    ip = models.GenericIPAddressField(
        verbose_name="IP-адрес"
    )
    user_agent = models.CharField(
        max_length=512,
        verbose_name="User-Agent"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name="Время входа"
    )

    class Meta:
        verbose_name = "История входов пользователя"
        verbose_name_plural = "Истории входов пользователей"
        ordering = ["-timestamp"]