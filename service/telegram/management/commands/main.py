import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from exchange.models import Vacancy
from telegram.models import BotSettings


class Command(BaseCommand):
    help = "Отправляет новые вакансии в Telegram-канал, используя настройки из модели BotSettings"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        # Получаем активные настройки через sync_to_async
        settings = await sync_to_async(self.get_active_settings)()
        if not settings:
            self.stderr.write("❌ Нет активных настроек бота.")
            return

        self.stdout.write(f"🔧 Используется бот: {settings.name}")
        await self.send_vacancies(settings)

    def get_active_settings(self):
        """Синхронный ORM-запрос для sync_to_async"""
        return BotSettings.objects.filter(is_active=True).first()

    def get_new_vacancies(self):
        """Синхронный ORM-запрос для sync_to_async"""
        return list(Vacancy.objects.all())

    async def send_vacancies(self, settings: BotSettings):
        bot = Bot(token=settings.bot_token)

        # Загружаем новые вакансии асинхронно
        new_vacancies = await sync_to_async(self.get_new_vacancies)()

        if not new_vacancies:
            self.stdout.write("✅ Новых вакансий нет.")
            await bot.session.close()
            return

        for vacancy in new_vacancies:
            text = (
                f"📢 <b>{vacancy.title}</b>\n"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💼 Откликнуться", url=vacancy.link)]
                ]
            )

            try:
                await bot.send_message(
                    chat_id=settings.channel_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

                # Помечаем как отправленную
                self.stdout.write(self.style.SUCCESS(f"✅ {vacancy.title} — отправлено"))
            except Exception as e:
                self.stderr.write(f"⚠️ Ошибка при отправке '{vacancy.title}': {e}")

        await bot.session.close()
        self.stdout.write(self.style.SUCCESS("🎯 Все новые вакансии успешно отправлены."))

