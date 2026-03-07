from django.contrib import admin
from .models import *


# Register your models here.
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "email",
        "role",
        "language",
        "region",
        "timezone",
        "consent_accepted",
        "last_activity",
    )

    list_filter = (
        "role",
        "consent_accepted",
        "region",
        "language",
        "timezone",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone_number",
    )

    readonly_fields = (
        "registration_date",
        "last_activity",
    )

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "email",
                    "role",
                    "phone_number",
                )
            },
        ),
        (
            "Telegram",
            {
                "fields": (
                    "telegram",
                )
            },
        ),
        (
            "Профиль",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "photo",
                )
            },
        ),
        (
            "Локализация",
            {
                "fields": (
                    "language",
                    "region",
                    "timezone",
                )
            },
        ),
        (
            "Статус",
            {
                "fields": (
                    "consent_accepted",
                    "is_superuser",
                    "is_staff",
                    "is_active",
                )
            },
        ),
        (
            "Шифрование",
            {
                "fields": (
                    "public_key",
                )
            },
        ),
        (
            "Системная информация",
            {
                "fields": (
                    "registration_date",
                    "last_activity",
                )
            },
        ),
    )

    ordering = ("-registration_date",)


@admin.register(UserLoginHistory)
class UserLoginHistoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    pass



@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    pass


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    pass