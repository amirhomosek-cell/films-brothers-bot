"""Подставляет в data флаги is_admin и is_owner (env + база)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.access import is_admin, is_owner
from bot.config import Config
from bot.db import Database


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        config: Config = data["config"]
        db: Database = data["db"]
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        user_id = user.id if user else None
        data["is_owner"] = is_owner(config, db, user_id)
        data["is_admin"] = is_admin(config, db, user_id)
        return await handler(event, data)
