"""Админ: статистика, рассылка, обязательная подписка на каналы."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db import Database
from bot.keyboards import (
    back_to_panel_keyboard,
    channels_menu_keyboard,
    confirm_broadcast_keyboard,
)
from bot.states import AddChannel, Broadcast
from bot.texts import t
from bot.utils import parse_channel_ref

logger = logging.getLogger(__name__)
router = Router(name="admin_tools")



# ---- /stats ----

@router.message(Command("stats"))
async def cmd_stats(message: Message, config: Config, db: Database, lang: str, is_admin: bool) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    s = db.stats()
    await message.answer(t(lang, "stats", **s))


# ---- /broadcast ----

@router.message(Command("broadcast"))
async def cmd_broadcast(
    message: Message, state: FSMContext, config: Config, lang: str,
    is_admin: bool
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    await state.clear()
    await state.set_state(Broadcast.waiting_message)
    await message.answer(t(lang, "broadcast_send"))


@router.message(StateFilter(Broadcast.waiting_message))
async def broadcast_got_message(
    message: Message, state: FSMContext, db: Database, lang: str
) -> None:
    count = db.count_users()
    if count == 0:
        await state.clear()
        await message.answer(t(lang, "broadcast_none"))
        return
    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id,
    )
    await state.set_state(Broadcast.confirm)
    await message.answer(
        t(lang, "broadcast_confirm", n=count),
        reply_markup=confirm_broadcast_keyboard(lang),
    )


@router.callback_query(StateFilter(Broadcast.confirm), F.data == "broadcast:yes")
async def broadcast_run(
    callback: CallbackQuery, state: FSMContext, db: Database, lang: str
) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.answer()
    from_chat = data.get("broadcast_chat_id")
    message_id = data.get("broadcast_message_id")
    if not from_chat or not message_id or not callback.message:
        await callback.message.answer(t(lang, "cancelled")) if callback.message else None
        return
    user_ids = db.all_user_ids()
    # Не шлём повторно тому, кто уже видел исходное сообщение в этом чате,
    # но админ может быть единственным — всё равно копируем всем, включая его.
    ok = 0
    fail = 0
    status = await callback.message.answer(
        t(lang, "broadcast_progress", done=0, total=len(user_ids))
    )
    for i, user_id in enumerate(user_ids, start=1):
        try:
            await callback.bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat,
                message_id=message_id,
            )
            ok += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 0.1)
            try:
                await callback.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=from_chat,
                    message_id=message_id,
                )
                ok += 1
            except TelegramAPIError:
                fail += 1
        except (TelegramForbiddenError, TelegramAPIError):
            fail += 1
        if i % 25 == 0 or i == len(user_ids):
            try:
                await status.edit_text(
                    t(lang, "broadcast_progress", done=i, total=len(user_ids))
                )
            except TelegramAPIError:
                pass
        await asyncio.sleep(0.05)
    await status.edit_text(t(lang, "broadcast_done", ok=ok, fail=fail))


# ---- /channels ----

def _channels_text(db: Database, lang: str) -> str:
    channels = db.list_channels()
    enabled = db.subscription_enabled()
    status = t(lang, "channels_on" if enabled else "channels_off")
    if channels:
        listing = "\n".join(
            t(
                lang,
                "channels_item",
                title=ch.title or ch.chat_id,
                chat_id=ch.chat_id,
            )
            for ch in channels
        )
    else:
        listing = t(lang, "channels_empty")
    return t(lang, "channels_menu", status=status, list=listing)


@router.message(Command("channels"))
async def cmd_channels(message: Message, config: Config, db: Database, lang: str, is_admin: bool) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    await message.answer(
        _channels_text(db, lang),
        reply_markup=channels_menu_keyboard(
            lang, db.list_channels(), db.subscription_enabled()
        ),
    )


@router.callback_query(F.data == "ch:toggle")
async def cb_toggle_sub(callback: CallbackQuery, config: Config, db: Database, lang: str, is_admin: bool) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    enabled = not db.subscription_enabled()
    db.set_subscription_enabled(enabled)
    key = "channels_toggled_on" if enabled else "channels_toggled_off"
    await callback.answer(t(lang, key))
    if callback.message:
        await callback.message.edit_text(
            _channels_text(db, lang),
            reply_markup=channels_menu_keyboard(
                lang, db.list_channels(), db.subscription_enabled()
            ),
        )


@router.callback_query(F.data == "ch:add")
async def cb_add_channel(
    callback: CallbackQuery, state: FSMContext, config: Config, lang: str,
    is_admin: bool
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    await state.set_state(AddChannel.waiting_channel)
    await callback.answer()
    if callback.message:
        await callback.message.answer(t(lang, "channels_add_ask"))


@router.callback_query(F.data.startswith("ch:rm:"))
async def cb_remove_channel(
    callback: CallbackQuery, config: Config, db: Database, lang: str,
    is_admin: bool
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return
    try:
        channel_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer()
        return
    db.remove_channel(channel_id)
    await callback.answer(t(lang, "channels_removed"))
    if callback.message:
        await callback.message.edit_text(
            _channels_text(db, lang),
            reply_markup=channels_menu_keyboard(
                lang, db.list_channels(), db.subscription_enabled()
            ),
        )


@router.message(StateFilter(AddChannel.waiting_channel), F.text, ~F.text.startswith("/"))
async def add_channel_got(
    message: Message, state: FSMContext, db: Database, lang: str
) -> None:
    ref = parse_channel_ref(message.text or "")
    if not ref:
        await message.answer(t(lang, "channels_invalid"))
        return
    if db.get_channel_by_chat_id(ref):
        await message.answer(t(lang, "channels_already"))
        return
    try:
        chat = await message.bot.get_chat(ref if ref.startswith("@") else int(ref))
    except (TelegramAPIError, ValueError) as exc:
        logger.info("get_chat failed for %s: %s", ref, exc)
        await message.answer(t(lang, "channels_bot_not_admin"))
        return
    # Проверяем, что бот может видеть участников (обычно нужен статус админа).
    try:
        me = await message.bot.get_me()
        member = await message.bot.get_chat_member(chat.id, me.id)
        if member.status not in {"administrator", "creator"}:
            await message.answer(t(lang, "channels_bot_not_admin"))
            return
    except TelegramAPIError:
        await message.answer(t(lang, "channels_bot_not_admin"))
        return

    title = chat.title or chat.full_name or ref
    url = None
    if chat.username:
        url = f"https://t.me/{chat.username}"
    else:
        try:
            invite = await message.bot.create_chat_invite_link(chat.id)
            url = invite.invite_link
        except TelegramAPIError as exc:
            logger.info("invite link failed for %s: %s", chat.id, exc)

    # Храним стабильный числовой id плюс, если есть, @username в url.
    chat_id = str(chat.id)
    if db.get_channel_by_chat_id(chat_id) or (chat.username and db.get_channel_by_chat_id("@" + chat.username)):
        await message.answer(t(lang, "channels_already"))
        await state.clear()
        return
    try:
        db.add_channel(chat_id, title=title, url=url)
    except ValueError as exc:
        await message.answer(t(lang, "channels_add_fail", error=str(exc)))
        return
    await state.clear()
    await message.answer(
        t(lang, "channels_added", title=title),
    )
    await message.answer(
        _channels_text(db, lang),
        reply_markup=channels_menu_keyboard(
            lang, db.list_channels(), db.subscription_enabled()
        ),
    )


@router.callback_query(F.data == "panel:stats")
async def cb_panel_stats(
    callback: CallbackQuery, is_admin: bool, db: Database, lang: str
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            t(lang, "stats", **db.stats()),
            reply_markup=back_to_panel_keyboard(lang),
        )


@router.callback_query(F.data == "panel:channels")
async def cb_panel_channels(
    callback: CallbackQuery, is_admin: bool, db: Database, lang: str
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            _channels_text(db, lang),
            reply_markup=channels_menu_keyboard(
                lang, db.list_channels(), db.subscription_enabled()
            ),
        )


@router.callback_query(F.data == "panel:broadcast")
async def cb_panel_broadcast(
    callback: CallbackQuery,
    state: FSMContext,
    is_admin: bool,
    lang: str,
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    await state.clear()
    await state.set_state(Broadcast.waiting_message)
    await callback.answer()
    if callback.message:
        await callback.message.answer(t(lang, "broadcast_send"))

