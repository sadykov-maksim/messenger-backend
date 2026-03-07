import asyncio
import logging
import sys
from typing import List

import betterlogging as bl
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, Message
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from backend.settings import env
from .config import load_config, Config
from .handlers import routers_list
from .middlewares.config import ConfigMiddleware
from .middlewares.check_auth import CheckUserMiddleware
from .services import broadcaster
from django.conf import settings


from asgiref.sync import sync_to_async
from telegram.models import BotSettings

# Webserver settings
# bind localhost only to prevent any external access
WEB_SERVER_HOST = env("WEB_SERVER_HOST")
# Port for incoming request from reverse proxy. Should be any available port
WEB_SERVER_PORT = env("WEB_SERVER_PORT")

# Path to webhook route, on which Telegram will send requests
WEBHOOK_PATH = env("WEBHOOK_PATH")
# Secret key to validate requests from Telegram (optional)
WEBHOOK_SECRET = env("WEBHOOK_SECRET")
# Base URL for webhook will be used to generate webhook URL for Telegram
BASE_WEBHOOK_URL = f"https://{settings.SITE_DOMAIN}{WEBHOOK_PATH}"
# Path to SSL certificate and private key for self-signed certificate.
WEBHOOK_SSL_CERT = env("WEBHOOK_SSL_CERT")
WEBHOOK_SSL_PRIV = env("WEBHOOK_SSL_PRIV")


async def on_startup(bot: Bot, admin_ids: list): # Имя совпадает с ключом в dp[...]
    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}", secret_token=WEBHOOK_SECRET)
    try:
        await broadcaster.broadcast(bot, admin_ids, "Бот був запущений")
    except Exception as e:
        logging.error(f"Failed to send startup message to {admin_ids}: {e}")

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook удален")


def register_global_middlewares(dp: Dispatcher, config: Config, session_pool=None):
    """
    Register global middlewares for the given dispatcher.
    Global middlewares here are the ones that are applied to all the handlers (you specify the type of update)

    :param dp: The dispatcher instance.
    :type dp: Dispatcher
    :param config: The configuration object from the loaded configuration.
    :param session_pool: Optional session pool object for the database using SQLAlchemy.
    :return: None
    """
    middleware_types = [
        ConfigMiddleware(config),
        #CheckUserMiddleware(),
        # DatabaseMiddleware(session_pool),
    ]

    for middleware_type in middleware_types:
        dp.message.outer_middleware(middleware_type)
        dp.callback_query.outer_middleware(middleware_type)


def setup_logging():
    """
    Set up logging configuration for the application.

    This method initializes the logging configuration for the application.
    It sets the log level to INFO and configures a basic colorized log for
    output. The log format includes the filename, line number, log level,
    timestamp, logger name, and log message.

    Returns:
        None

    Example usage:
        setup_logging()
    """
    log_level = logging.INFO
    bl.basic_colorized_config(level=log_level)

    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot")


def get_storage(bot_settings: BotSettings):
    """
    Возвращает объект Storage на основе настроек из модели BotSettings.

    Args:
        bot_settings (BotSettings): объект с настройками бота и Redis.

    Returns:
        Storage: RedisStorage или MemoryStorage
    """
    if bot_settings.use_redis and bot_settings.redis_host and bot_settings.redis_port:
        dsn = bot_settings.redis_dsn()
        return RedisStorage.from_url(
            dsn,
            key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True)
        )
    else:
        return MemoryStorage()


def main() -> None:
    setup_logging()
    bot_settings = BotSettings.get_active()
    bot = Bot(
        token=bot_settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    storage = get_storage(bot_settings)

    admin_ids = BotSettings.get_admin_ids()
    logging.info(admin_ids)
    dp = Dispatcher(storage=storage, admin_ids=[])



    dp.include_routers(*routers_list)
    register_global_middlewares(dp, bot_settings)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()