"""Управление администраторами и вход в админ-панель."""

from __future__ import annotations

import html
import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, MessageOriginHiddenUser, MessageOriginUser, User

from bot.access import (
    display_name,
    is_admin as user_is_admin,
    is_env_owner,
    is_owner as user_is_owner,
)
from bot.config import Config
from bot.db import Database
from bot.keyboards import (
    admin_card_keyboard,
    admin_panel_keyboard,
    admins_back_keyboard,
    admins_menu_keyboard,
    confirm_add_admin_keyboard,
    confirm_del_admin_keyboard,
    confirm_set_role_keyboard,
)
from bot.states import SetAdmin
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


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def admins_text(db: Database, config: Config, lang: str, *, owner: bool = False) -> str:
    items = db.list_admins(config.admin_ids)
    lines = [t(lang, "admins_title"), ""]
    extras = 0
    for admin in items:
        name = _esc(display_name(
            user_id=admin.user_id,
            first_name=admin.first_name,
            username=admin.username,
        ))
        key = "admins_owner_line" if admin.is_owner else "admins_line"
        if not admin.is_owner:
            extras += 1
        lines.append(t(lang, key, name=name, user_id=admin.user_id))
    if extras == 0 and any(a.is_owner for a in items):
        lines.append("")
        lines.append(t(lang, "admins_empty"))
    if owner and any(not a.env_owner for a in items):
        lines.append("")
        lines.append(t(lang, "admins_manage_hint"))
    return "\n".join(lines)


def admins_markup(db: Database, config: Config, lang: str, owner: bool):
    return admins_menu_keyboard(lang, db.list_admins(config.admin_ids), owner=owner)


def plan_role_change(config: Config, db: Database, user_id: int, role: str) -> str:
    """Что сделать, если главный админ выбрал пользователя для роли role ('admin'/'owner').

    Возвращает ключ texts: owner_env_protected, addadmin_already_owner, addadmin_already
    (менять нечего) либо setowner_confirm, demote_confirm, addadmin_confirm (спросить).
    """
    if is_env_owner(config, user_id):
        return "owner_env_protected"
    db_owner = db.is_db_owner(user_id)
    db_admin = db.is_db_admin(user_id)
    if role == "owner":
        return "addadmin_already_owner" if db_owner else "setowner_confirm"
    if db_owner:
        return "demote_confirm"
    if db_admin:
        return "addadmin_already"
    return "addadmin_confirm"


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
async def cmd_admins(
    message: Message, is_admin: bool, is_owner: bool, db: Database, config: Config, lang: str
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    await message.answer(
        admins_text(db, config, lang, owner=is_owner),
        reply_markup=admins_markup(db, config, lang, is_owner),
    )


@router.callback_query(F.data == "panel:admins")
async def cb_panel_admins(
    callback: CallbackQuery,
    is_admin: bool,
    is_owner: bool,
    db: Database,
    config: Config,
    lang: str,
    state: FSMContext | None = None,
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if state is not None and await state.get_state() == SetAdmin.waiting_user.state:
        await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            admins_text(db, config, lang, owner=is_owner),
            reply_markup=admins_markup(db, config, lang, is_owner),
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
    if user_is_owner(config, db, user_id):
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
    if user_is_owner(config, db, user_id):
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
    if is_env_owner(config, user_id):
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
    if is_env_owner(config, user_id):
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, "deladmin_owner"))
        return
    name = _profile_name(db, user_id)
    removed = db.remove_db_admin(user_id)
    await callback.answer()
    text = t(lang, "deladmin_done", name=_esc(name)) if removed else t(lang, "deladmin_not_found")
    if callback.message:
        await callback.message.edit_text(text, reply_markup=admins_back_keyboard(lang))


# --- кнопки «Сделать админом» / «Сделать главным админом» ---

_ROLES = ("admin", "owner")


async def _deny(callback: CallbackQuery, is_admin: bool, is_owner: bool, lang: str) -> bool:
    """True, если доступ запрещён (ответ уже отправлен)."""
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return True
    if not is_owner:
        await callback.answer(t(lang, "owner_only"), show_alert=True)
        return True
    return False


def _parse_tail_id(data: str | None) -> int | None:
    try:
        value = int((data or "").rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return None
    return value if value > 0 else None


@router.callback_query(F.data.in_({"adm:new:admin", "adm:new:owner"}))
async def cb_admin_new(
    callback: CallbackQuery, state: FSMContext, is_admin: bool, is_owner: bool, lang: str
) -> None:
    if await _deny(callback, is_admin, is_owner, lang):
        return
    role = (callback.data or "").rsplit(":", 1)[1]
    await state.set_state(SetAdmin.waiting_user)
    await state.update_data(role=role)
    await callback.answer()
    if callback.message:
        await callback.message.answer(t(lang, f"setadmin_ask_{role}"))


@router.message(StateFilter(SetAdmin.waiting_user), ~F.text.startswith("/"))
async def setadmin_got_user(
    message: Message,
    state: FSMContext,
    is_admin: bool,
    is_owner: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if not is_admin or not is_owner:
        await state.clear()
        await message.answer(t(lang, "owner_only" if is_admin else "admin_only"))
        return
    data = await state.get_data()
    role = data.get("role") if data.get("role") in _ROLES else "admin"
    target = resolve_target(message, message.text or message.caption, db)
    if isinstance(target, str):
        key = f"setadmin_ask_{role}" if target == "addadmin_usage" else target
        extra = {}
        if key == "addadmin_username_not_found":
            extra["username"] = (message.text or "").lstrip("@").strip()
        await message.answer(t(lang, key, **extra))
        return  # остаёмся в ожидании, можно прислать ещё раз
    user_id, username, first_name = target
    name = _esc(_profile_name(db, user_id, username, first_name))
    plan = plan_role_change(config, db, user_id, role)
    await state.clear()
    if plan == "setowner_confirm":
        markup = confirm_set_role_keyboard(lang, user_id, "owner", "btn_yes_setowner")
    elif plan == "demote_confirm":
        markup = confirm_set_role_keyboard(lang, user_id, "admin", "btn_yes_demote")
    elif plan == "addadmin_confirm":
        markup = confirm_set_role_keyboard(lang, user_id, "admin", "btn_yes_addadmin")
    else:
        await message.answer(t(lang, plan), reply_markup=admins_back_keyboard(lang))
        return
    await message.answer(t(lang, plan, name=name, user_id=user_id), reply_markup=markup)


@router.callback_query(F.data.startswith("adm:card:"))
async def cb_admin_card(
    callback: CallbackQuery,
    is_admin: bool,
    is_owner: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if await _deny(callback, is_admin, is_owner, lang):
        return
    user_id = _parse_tail_id(callback.data)
    if user_id is None:
        await callback.answer()
        return
    if is_env_owner(config, user_id):
        await callback.answer(t(lang, "owner_env_protected"), show_alert=True)
        return
    if not db.is_db_admin(user_id):
        await callback.answer(t(lang, "deladmin_not_found"), show_alert=True)
        return
    await callback.answer()
    owner = db.is_db_owner(user_id)
    text = t(
        lang,
        "admin_card",
        mark="⭐" if owner else "👤",
        name=_esc(_profile_name(db, user_id)),
        user_id=user_id,
        role=t(lang, "role_owner" if owner else "role_admin"),
    )
    if callback.message:
        await callback.message.edit_text(
            text, reply_markup=admin_card_keyboard(lang, user_id, is_owner=owner)
        )


@router.callback_query(F.data.startswith("adm:set:"))
async def cb_admin_set_role(
    callback: CallbackQuery,
    is_admin: bool,
    is_owner: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if await _deny(callback, is_admin, is_owner, lang):
        return
    parts = (callback.data or "").split(":")
    user_id = _parse_tail_id(callback.data)
    if len(parts) != 4 or parts[2] not in _ROLES or user_id is None:
        await callback.answer()
        return
    role = parts[2]
    back = admins_back_keyboard(lang)
    if is_env_owner(config, user_id):
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, "owner_env_protected"), reply_markup=back)
        return
    was_admin = db.is_db_admin(user_id)
    row = db.get_user(user_id)
    username = row["username"] if row else None
    added_by = callback.from_user.id if callback.from_user else None
    changed = db.set_admin_role(
        user_id, owner=(role == "owner"), added_by=added_by, username=username
    )
    name = _esc(_profile_name(db, user_id))
    if not changed:
        key = "addadmin_already_owner" if role == "owner" else "addadmin_already"
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(t(lang, key), reply_markup=back)
        return
    if role == "owner":
        text = t(lang, "setowner_done", name=name)
        notify_key = "setowner_notify"
    elif was_admin:
        text = t(lang, "demote_done", name=name)
        notify_key = None
    else:
        text = t(lang, "addadmin_done", name=name)
        notify_key = "addadmin_notify"
    if notify_key:
        try:
            await callback.bot.send_message(user_id, t(db.get_language(user_id), notify_key))
        except (TelegramForbiddenError, TelegramAPIError) as exc:
            logger.info("Could not notify admin %s: %s", user_id, exc)
            text += "\n\n" + t(lang, "addadmin_notify_fail")
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=back)


@router.callback_query(F.data.startswith("adm:del:"))
async def cb_admin_del(
    callback: CallbackQuery,
    is_admin: bool,
    is_owner: bool,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if await _deny(callback, is_admin, is_owner, lang):
        return
    user_id = _parse_tail_id(callback.data)
    if user_id is None:
        await callback.answer()
        return
    if is_env_owner(config, user_id):
        await callback.answer(t(lang, "owner_env_protected"), show_alert=True)
        return
    if not db.is_db_admin(user_id):
        await callback.answer(t(lang, "deladmin_not_found"), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            t(lang, "deladmin_confirm", name=_esc(_profile_name(db, user_id)), user_id=user_id),
            reply_markup=confirm_del_admin_keyboard(lang, user_id),
        )
