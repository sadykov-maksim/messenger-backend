from aiogram import F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async

from telegram.management.commands.handlers.callback_data import MenuCbData, MenuActions


# This is a simple keyboard, that contains 2 buttons
def greeting_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Стартуем", callback_data="start_onboarding")],
        ]
    )

def rules_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Пользовательское соглашение", web_app=WebAppInfo(url="https://app.telebotic.ru/docs/privacy"))],
            [
                InlineKeyboardButton(text="✅ Принимаю", callback_data="rules_accept"),
                InlineKeyboardButton(text="❌ Не согласен", callback_data="rules_decline")
            ],
        ]
    )

def privacy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Политика конфиденциальности", web_app=WebAppInfo(url="https://app.telebotic.ru/docs/privacy"))],

        ]
    )


def subscription_keyboard(channel_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📣 Подписаться на канал", url=f"{channel_id}"),
            ],
            [
                InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscribed"),
                InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_subscription"),
            ],
        ]
    )

def telegram_channel_keyboard(channel_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖️ Телеботик.ру Сообщество", url=f"{channel_id}"),
            ],
        ]
    )

def finish_registration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Завершить регистрацию", callback_data="finish_registration")],
        ]
    )

def mistakes_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Начать сначала",  callback_data=MenuCbData(action=MenuActions.root).pack())],
            [InlineKeyboardButton(text="🛠 Сообщить об ошибке", callback_data=MenuCbData(action=MenuActions.help).pack())]
        ]
    )

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(
        text="🚀 Запустить приложение",
        web_app=WebAppInfo(url="https://app.telebotic.ru/mini-app/"))
    )

    return builder.as_markup()

