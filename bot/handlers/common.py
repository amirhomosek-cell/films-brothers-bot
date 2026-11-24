"""Старт, язык, справка, отмена FSM."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup

from bot.access import is_admin as user_is_admin
from bot.config import Config
from bot.db import Database
from bot.keyboards import admin_entry_keyboard, language_keyboard
from bot.texts import t

router = Router(name="common")


def help_markup(lang: str, user_id: int | None, config: Config, db: Database) -> InlineKeyboardMarkup | None:
    if user_is_admin(config, db, user_id):
        return admin_entry_keyboard(lang)
    return None


def help_text(lang: str, user_id: int | None, config: Config, db: Database) -> str:
    text = t(lang, "help")
    if user_is_admin(config, db, user_id):
        text += t(lang, "help_admin")
    return text


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "choose_lang"), reply_markup=language_keyboard())


@router.message(Command("lang"))
async def cmd_lang(message: Message, lang: str) -> None:
    await message.answer(t(lang, "choose_lang"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def cb_language(
    callback: CallbackQuery,
    db: Database,
    config: Config,
    lang: str,
) -> None:
    if not callback.data or not callback.from_user:
        await callback.answer()
        return
    new_lang = callback.data.split(":", 1)[1]
    if new_lang not in {"ru", "uz"}:
        await callback.answer()
        return
    db.set_language(callback.from_user.id, new_lang)
    await callback.answer()
    uid = callback.from_user.id
    text = t(new_lang, "lang_saved") + "\n\n" + help_text(new_lang, uid, config, db)
    markup = help_markup(new_lang, uid, config, db)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=markup)
    else:
        await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str, config: Config, db: Database) -> None:
    user_id = message.from_user.id if message.from_user else None
    await message.answer(
        help_text(lang, user_id, config, db),
        reply_markup=help_markup(lang, user_id, config, db),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str) -> None:
    current = await state.get_state()
    await state.clear()
    if current:
        await message.answer(t(lang, "cancelled"))
    else:
        await message.answer(t(lang, "nothing_to_cancel"))


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.clear()
    await callback.answer(t(lang, "cancelled"))
    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer(t(lang, "cancelled"))
