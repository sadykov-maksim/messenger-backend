import logging
import os

import django


# Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from telegram.management.commands.core import main

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("🤖 Запуск Telegram-бота")
        main()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка Telegram-бота: {e}", exc_info=True)
