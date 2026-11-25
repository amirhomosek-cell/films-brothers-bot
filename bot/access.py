"""Проверка прав: главные админы из .env и из базы, плюс обычные админы из базы."""

from __future__ import annotations

from bot.config import Config
from bot.db import Database


def is_env_owner(config: Config, user_id: int | None) -> bool:
    """Главный администратор, прописанный в ADMIN_IDS (его нельзя понизить или удалить)."""
    return user_id is not None and user_id in config.admin_ids


def is_owner(config: Config, db: Database, user_id: int | None) -> bool:
    """Главный администратор: из ADMIN_IDS или назначенный через бота."""
    if user_id is None:
        return False
    if is_env_owner(config, user_id):
        return True
    return db.is_db_owner(user_id)


def is_admin(config: Config, db: Database, user_id: int | None) -> bool:
    """Админ, если он в ADMIN_IDS или в таблице admins."""
    if user_id is None:
        return False
    if is_env_owner(config, user_id):
        return True
    return db.is_db_admin(user_id)


def display_name(
    *,
    user_id: int,
    first_name: str | None = None,
    username: str | None = None,
) -> str:
    username = (username or "").lstrip("@").strip() or None
    first_name = (first_name or "").strip() or None
    if first_name and username:
        return f"{first_name} (@{username})"
    if first_name:
        return first_name
    if username:
        return f"@{username}"
    return f"ID {user_id}"
