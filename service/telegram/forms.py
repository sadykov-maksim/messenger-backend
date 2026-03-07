from django import forms
from django.contrib import admin
from .models import BotSettings, TelegramUser


class BotSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = BotSettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["admins"].queryset = TelegramUser.objects.filter(
            role=TelegramUser.Role.ADMIN
        )
