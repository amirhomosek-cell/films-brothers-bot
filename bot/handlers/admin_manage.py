"""Управление администраторами и вход в админ-панель."""

from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, MessageOriginHiddenUser, MessageOriginUser, User

from bot.access import display_name, is_admin as user_is_admin, is_owner as user_is_owner
from bot.config import Config
from bot.db import Database
from bot.keyboards import (
    admin_panel_keyboard,
    back_to_panel_keyboard,
    confirm_add_admin_keyboard,
    confirm_del_admin_keyboard,
)
from bot.texts import t

logger = logging.getLogger(__name__)
router = Router(name="admin_manage")

_USERNAME_RE = re.compile(r"^@?[A-Za-z][A-Za-z0-9_]{3,31}$")


def _profile_name(db: Database, user_id: int, username: str | None = None, first_name: str | None = None) -> str:
    row = db.get_user(user_id)
    if row:
        first_name = first_name or row["first_name"]
        username = username or row["username"]
    return display_name(user_id=user_id, first_name=first_name, username=username)


def admins_text(db: Database, config: Config, lang: str) -> str:
    items = db.list_admins(config.admin_ids)
    lines = [t(lang, "admins_title"), ""]
    extras = 0
    for admin in items:
        name = display_name(
            user_id=admin.user_id,
            first_name=admin.first_name,
            username=admin.username,
        )
        key = "admins_owner_line" if admin.is_owner else "admins_line"
        if not admin.is_owner:
            extras += 1
        lines.append(t(lang, key, name=name, user_id=admin.user_id))
    if extras == 0 and any(a.is_owner for a in items):
        lines.append("")
        lines.append(t(lang, "admins_empty"))
    return "\n".join(lines)


def panel_text(lang: str) -> str:
    return t(lang, "admin_panel_title")


def _origin_user(message: Message) -> User | None | str:
    """Возвращает User, 'hidden' если скрыт, иначе None."""
    origin = message.forward_origin
    if isinstance(origin, MessageOriginHiddenUser):
        return "hidden"
    if isinstance(origin, MessageOriginUser):
        return origin.sender_user
    if message.forward_from:
        return message.forward_from
    return None


def resolve_target(
    message: Message,
    args: str | None,
    db: Database,
) -> tuple[int, str | None, str | None] | str:
    """ID, username, first_name или ключ ошибки texts."""
    reply = message.reply_to_message
    if reply:
        origin = _origin_user(reply)
        if origin == "hidden":
            return "addadmin_hidden"
        if isinstance(origin, User):
            if origin.is_bot:
                return "addadmin_bot"
            return origin.id, origin.username, origin.first_name
        if reply.from_user and not reply.from_user.is_bot:
            u = reply.from_user
            return u.id, u.username, u.first_name
        if reply.from_user and reply.from_user.is_bot:
            return "addadmin_bot"

    origin = _origin_user(message)
    if origin == "hidden":
        return "addadmin_hidden"
    if isinstance(origin, User):
        if origin.is_bot:
            return "addadmin_bot"
        return origin.id, origin.username, origin.first_name

    raw = (args or "").strip()
    if not raw:
        return "addadmin_usage"
    if raw.isdigit():
        user_id = int(raw)
        if user_id < 1:
            return "addadmin_invalid"
        row = db.get_user(user_id)
        return (
            user_id,
            row["username"] if row else None,
            row["first_name"] if row else None,
        )
    if _USERNAME_RE.match(raw):
        row = db.find_user_by_username(raw)
        if not row:
            return "addadmin_username_not_found"
        return int(row["user_id"]), row["username"], row["first_name"]
    return "addadmin_invalid"


@router.message(Command("admin", "panel"))
async def cmd_admin(message: Message, is_admin: bool, lang: str) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    await message.answer(panel_text(lang), reply_markup=admin_panel_keyboard(lang))


@router.callback_query(F.data == "panel:home")
async def cb_panel_home(callback: CallbackQuery, is_admin: bool, lang: str) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            panel_text(lang), reply_markup=admin_panel_keyboard(lang)
        )


@router.message(Command("admins"))
async def cmd_admins(message: Message, is_admin: bool, db: Database, config: Config, lang: str) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    await message.answer(
        admins_text(db, config, lang),
        reply_markup=back_to_panel_keyboard(lang),
    )


@router.callback_query(F.data == "panel:admins")
async def cb_panel_admins(
    callback: CallbackQuery, is_admin: bool, db: Database, config: Config, lang: str
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            admins_text(db, config, lang),
            reply_markup=back_to_panel_keyboard(lang),
        )


@router.message(Command("addadmin"))
async def cmd_addadmin(
    message: Message,
    command: CommandObject,
    is_owner: bool,
    is_admin: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    if not is_owner:
        await message.answer(t(lang, "owner_only"))
        return
    target = resolve_target(message, command.args, db)
    if isinstance(target, str):
        extra = {}
        if target == "addadmin_username_not_found":
            extra["username"] = (command.args or "").lstrip("@").strip()
        await message.answer(t(lang, target, **extra))
        return
    user_id, username, first_name = target
    name = _profile_name(db, user_id, username, first_name)
    if user_is_owner(config, user_id):
        await message.answer(t(lang, "addadmin_already_owner"))
        return
    if user_is_admin(config, db, user_id):
        await message.answer(t(lang, "addadmin_already"))
        return
    await message.answer(
        t(lang, "addadmin_confirm", name=name, user_id=user_id),
        reply_markup=confirm_add_admin_keyboard(lang, user_id),
    )


@router.callback_query(F.data.startswith("addadmin:yes:"))
async def cb_addadmin_yes(
    callback: CallbackQuery,
    is_owner: bool,
    is_admin: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not is_owner:
        await callback.answer(t(lang, "owner_only"), show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return
    try:
        user_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    if user_is_owner(config, user_id):
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, "addadmin_already_owner"))
        return
    if user_is_admin(config, db, user_id):
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, "addadmin_already"))
        return
    row = db.get_user(user_id)
    username = row["username"] if row else None
    first_name = row["first_name"] if row else None
    name = display_name(user_id=user_id, first_name=first_name, username=username)
    added_by = callback.from_user.id if callback.from_user else None
    try:
        db.add_admin(user_id, added_by=added_by, username=username)
    except ValueError:
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, "addadmin_already"))
        return
    notify_ok = False
    target_lang = db.get_language(user_id)
    try:
        await callback.bot.send_message(user_id, t(target_lang, "addadmin_notify"))
        notify_ok = True
    except (TelegramForbiddenError, TelegramAPIError) as exc:
        logger.info("Could not notify new admin %s: %s", user_id, exc)
    await callback.answer()
    text = t(lang, "addadmin_done", name=name)
    if not notify_ok:
        text += "\n\n" + t(lang, "addadmin_notify_fail")
    if callback.message:
        await callback.message.edit_text(text)


@router.message(Command("deladmin"))
async def cmd_deladmin(
    message: Message,
    command: CommandObject,
    is_owner: bool,
    is_admin: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    if not is_owner:
        await message.answer(t(lang, "owner_only"))
        return
    target = resolve_target(message, command.args, db)
    if isinstance(target, str):
        # reuse usage key for empty args
        key = "deladmin_usage" if target == "addadmin_usage" else target
        extra = {}
        if key == "addadmin_username_not_found":
            extra["username"] = (command.args or "").lstrip("@").strip()
        await message.answer(t(lang, key, **extra))
        return
    user_id, username, first_name = target
    name = _profile_name(db, user_id, username, first_name)
    if user_is_owner(config, user_id):
        await message.answer(t(lang, "deladmin_owner"))
        return
    if not db.is_db_admin(user_id):
        await message.answer(t(lang, "deladmin_not_found"))
        return
    await message.answer(
        t(lang, "deladmin_confirm", name=name, user_id=user_id),
        reply_markup=confirm_del_admin_keyboard(lang, user_id),
    )


@router.callback_query(F.data.startswith("deladmin:yes:"))
async def cb_deladmin_yes(
    callback: CallbackQuery,
    is_owner: bool,
    is_admin: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not is_owner:
        await callback.answer(t(lang, "owner_only"), show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return
    try:
        user_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    if user_is_owner(config, user_id):
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, "deladmin_owner"))
        return
    name = _profile_name(db, user_id)
    removed = db.remove_db_admin(user_id)
    await callback.answer()
    text = t(lang, "deladmin_done", name=name) if removed else t(lang, "deladmin_not_found")
    if callback.message:
        await callback.message.edit_text(text)
