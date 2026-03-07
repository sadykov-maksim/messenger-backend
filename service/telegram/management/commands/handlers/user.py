import asyncio
import logging

from asgiref.sync import sync_to_async

from aiogram import F, Bot, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
ReactionTypeEmoji,
    WebAppInfo,
)

from .helper.navigation import show_navigation
from .helper.subscribed import is_user_subscribed

from ..date_access.user import (
    change_consent_status,
    get_active_channel,
    get_or_create_user, change_finish_status, get_current_user,
)

from ..keyboards.inline import *

logger = logging.getLogger(__name__)

user_router = Router()


@user_router.message(CommandStart())
async def user_start(message: Message, command: CommandObject):
    """123"""

    username = message.from_user.username or "друг"
    ref_code = (command.args or "").strip() or None
    existing_user, created = await get_or_create_user(message, ref_code)

    if not existing_user.onboarding_completed:
        await message.answer(
            "Я — бот сервиса «Телеботик.ру».\n\n"
            "Здесь ты сможешь:\n"
            "• Создавать Telegram-ботов без кода\n"
            "• Настраивать их быстро и просто\n"
            "• Использовать готовые шаблоны для бизнеса\n\n"
            "Если готов — жми кнопку «🚀 Стартуем»",
            reply_markup=greeting_keyboard(),
        )
        return

    if not existing_user.consent_accepted:
        await message.answer(
            text="<b>Для продолжения работы с ботом необходимо ваше согласие на обработку персональных данных.</b>\n\n"
                 "Без этого вы не сможете использовать сервис.",
            reply_markup=rules_keyboard(),
            parse_mode="HTML",
        )
        return

    if not existing_user.registration_completed:
        await message.answer(
            "<b>Нужно завершить регистрацию.</b>\n\n"
            "Без этого вы не сможете использовать сервис.",
            reply_markup=finish_registration_keyboard(),
            parse_mode="HTML",
        )
        return

    await show_navigation(message)


@user_router.callback_query(F.data == "start_onboarding")
async def onboarding_start(callback: CallbackQuery):
    user = await get_current_user(callback)
    user.onboarding_completed = True
    await user.asave(update_fields=["onboarding_completed"])

    await callback.message.edit_text(
        "<b>📜 Пользовательское соглашение</b>\n\n"
        "Чтобы продолжить, подтвердите согласие с <b>правилами сервиса</b> и "
        "<b>обработкой персональных данных</b>.\n\n"
        "• Сервис предназначен для пользователей <b>18+</b>.\n"
        "• Данные используются <b>только</b> для работы сервиса и не передаются третьим лицам "
        "без <u>законных оснований</u>.\n"
        "• Запрещены <b>мошенничество</b>, <b>оскорбления</b> и другой <b>противоправный контент</b>.\n"
        "• Пользователь несёт <b>ответственность</b> за свои действия и публикуемые материалы.\n\n"
        "<i>Нажмите «Согласен(а)», чтобы продолжить.</i>",
        reply_markup=rules_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@user_router.callback_query(F.data == "rules_accept")
async def rules_accept(callback: CallbackQuery):
    await change_consent_status(callback.from_user.id, True)
    channel = await get_active_channel()

    if not channel:
        await callback.answer("Канал не настроен. Напиши в поддержку 🙏", show_alert=True)
        return

    await callback.message.edit_text(
        "Чтобы продолжить, подписка на канал необязательна.\n\n"
        "В нём ты найдёшь небанальные советы по поиску работы за границей, "
        "реальные истории людей и много вдохновения! ✨\n\n"
        "Если уже подписался(ась), нажми кнопку ниже:",
        reply_markup=subscription_keyboard(channel.channel_url),
    )
    await callback.answer()


@user_router.callback_query(F.data == "rules_decline")
async def rules_decline(callback: CallbackQuery):
    status = await change_consent_status(callback.from_user.id, False)

    await callback.message.edit_text(
        "Чтобы продолжить, нам нужно твоё <b>согласие</b> с <b>правилами и обработкой данных.</b>\n\n"
        "Без этого мы не сможем <b>сохранить информацию о тебе</b> и дальше <b>продолжить взаимодействие.</b>\n\n"
        "Если передумаешь — просто снова отправь <code>/start</code> и пройди регистрацию заново.",
        reply_markup=None,
        parse_mode="HTML",
    )
    await callback.answer()



@user_router.callback_query(F.data == "check_subscribed")
async def check_subscribed(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    channel = await get_active_channel()

    subscribed = await is_user_subscribed(bot, channel.channel_id, user_id)
    if not subscribed:
        await callback.answer("Сначала подпишись на канал, потом нажми «Проверить» 🙂", show_alert=True)
        await callback.message.edit_text(
            "Подписка на канал <b>не обязательна</b> — можно продолжить и без неё.\n\n"
            "А если вдруг захочется иногда читать новости, полезные заметки и видеть новые вакансии, "
            "мы будем рады видеть тебя в нашем Telegram-канале 👇\n\n"
            "Если уже подписался, нажми <b>«✅ Проверить подписку».</b>",
            parse_mode="HTML",
            reply_markup=subscription_keyboard(subscribed),
        )
        return

    await callback.message.answer(
        f"Спасибо за подписку 🙌\n\n"
        "Осталось совсем немного, и можно будет переходить к работе с сервисом.\n\n"
        "Для этого тебе необходимо активировать свою учетную запись, нажав на кнопку ниже.\n\n",
        parse_mode="Markdown",
        reply_markup=finish_registration_keyboard(),
    )
    await callback.answer()


@user_router.callback_query(F.data == "skip_subscription")
async def skip_subscription_handler(callback: CallbackQuery):
    channel = await get_active_channel()
    first_name = callback.from_user.first_name or "друг"

    await callback.message.edit_text(
        "<b>Хорошо, без проблем 🙂</b>\n\n"
        "Ты можешь продолжить без подписки — всё основное будет доступно и так.\n"
        "Если позже захочется заглянуть в канал за советами, историями или вакансиями — он всегда открыт для тебя.\n",
        parse_mode="HTML",
        reply_markup=telegram_channel_keyboard(channel.channel_url),
    )
    await asyncio.sleep(1.5)
    await callback.message.answer(
        f"⏳ Регистрация почти завершена, {first_name}!\n\n"
        "Осталось совсем немного, и можно будет переходить к работе с сервисом.\n\n"
        "Для этого тебе необходимо активировать свою учетную запись, нажав на кнопку ниже.\n\n",
        parse_mode="Markdown",
        reply_markup=finish_registration_keyboard(),
    )
    await callback.answer()


@user_router.callback_query(F.data == "finish_registration")
async def finish_registration_handler(callback: CallbackQuery):
    await callback.answer()
    final_status = await change_finish_status(callback.from_user.id, True)

    message = await callback.message.answer(
        text=("🎉 <b>Регистрация завершена!</b>\n\n"
        "Рады, что ты с нами! Теперь ты можешь пользоваться <b>всеми функциями</b> сервиса «<b>Телеботик.ру</b>». 🙌\n\n"
        "Спасибо, что <b>выбираешь нас</b> — мы постараемся сделать твой опыт <b>максимально удобным</b> и <b>полезным</b>. 🚀\n\n"
        "Если возникнут вопросы, <b>поддержка всегда на связи</b>. 👇"),
        message_effect_id="5046509860389126442",
        parse_mode="HTML"
    )
    await asyncio.sleep(1.5)
    await callback.bot.set_message_reaction(
        chat_id=callback.from_user.id,
        message_id=message.message_id,
        reaction=[ReactionTypeEmoji(emoji='❤')],
    )


@user_router.callback_query(F.data == "open_main_menu")
async def open_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 Добро пожаловать в главное меню!\n\n"
        "Выбери, с чего начнём 👇",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
