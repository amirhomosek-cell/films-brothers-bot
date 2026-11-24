"""Точка входа Telegram-бота поиска фильмов по коду."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Config, load_config
from bot.db import Database
from bot.handlers import admin_manage, admin_movies, admin_tools, common, user
from bot.health import start_health_server
from bot.middlewares.access import AccessMiddleware
from bot.middlewares.user import UserMiddleware

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("aiogram").setLevel(logging.INFO)


def create_dispatcher(config: Config, db: Database) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["config"] = config
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())
    # Порядок важен: команды и FSM рассылки раньше, чем «видео = добавить фильм».
    dp.include_router(common.router)
    dp.include_router(admin_manage.router)
    dp.include_router(admin_tools.router)
    dp.include_router(admin_movies.router)
    dp.include_router(user.router)
    return dp


async def run(config: Config) -> None:
    db = Database(config.db_path)
    if config.required_channels:
        added = db.seed_required_channels(config.required_channels)
        db.set_subscription_enabled(True)
        logger.info(
            "REQUIRED_CHANNELS: добавлено %s, всего задано %s, подписка включена",
            added,
            len(config.required_channels),
        )
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher(config, db)
    logger.info(
        "Бот запущен. Главные админы: %s. База: %s",
        ", ".join(str(i) for i in sorted(config.admin_ids)) or "—",
        config.db_path,
    )
    http_runner = None
    if config.port is not None:
        http_runner = await start_health_server(config.port)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        if http_runner is not None:
            await http_runner.cleanup()
        await bot.session.close()
        db.close()


def main() -> None:
    setup_logging()
    config = load_config(require_token=True)
    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        logger.info("Остановка по Ctrl+C")


if __name__ == "__main__":
    main()
