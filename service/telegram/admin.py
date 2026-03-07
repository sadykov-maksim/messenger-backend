from django.contrib import admin

from .forms import BotSettingsAdminForm
from .models import *


# Register your models here.
@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    form = BotSettingsAdminForm

    list_display = (
        "name",
        "is_active",
        "use_redis",
        "channel_id",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "use_redis",
    )

    search_fields = (
        "name",
        "channel_id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    filter_horizontal = ("admins",)

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "name",
                )
            },
        ),
        (
            "Telegram бот",
            {
                "fields": (
                    "bot_token",
                ),
                "description": (
                    "Токен Telegram-бота. "
                ),
            },
        ),
        (
            "Администраторы бота",
            {
                "fields": (
                    "admins",
                ),
            },
        ),
        (
            "Хранилище состояний (Redis)",
            {
                "fields": (
                    "redis_host",
                    "redis_port",
                    "redis_pass",
                    "use_redis",
                ),
                "description": (
                    "Используется для хранения FSM/сессий. "
                    "Если Redis не используется — поля можно оставить пустыми."
                ),
            },
        ),
        (
            "Канал / подписка",
            {
                "fields": (
                    "channel_url",
                    "channel_id",
                ),
                "description": (
                    "Настройки канала, обязательного для подписки."
                ),
            },
        ),
        (
            "Дополнительно",
            {
                "fields": (
                    "other_params",
                ),
            },
        ),
        (
            "Служебная информация",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "is_active",
                ),
            },
        ),
    )

    ordering = ("-created_at",)

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "telegram_id",
        "username",
        "first_name",
        "last_name",
    )

    search_fields = (
        "telegram_id",
        "username",
        "first_name",
        "last_name",
    )

    readonly_fields = (
        "telegram_id",
    )

    fieldsets = (
        (
            "Telegram профиль",
            {
                "fields": (
                    "telegram_id",
                    "username",
                    "first_name",
                    "last_name",
                    "photo",
                )
            },
        ),
    )