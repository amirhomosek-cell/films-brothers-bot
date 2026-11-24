"""Админ: добавление, удаление, редактирование и список фильмов."""

from __future__ import annotations

import logging
import math

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Config
from bot.db import Database, Movie
from bot.keyboards import (
    confirm_delete_keyboard,
    edit_menu_keyboard,
    list_keyboard,
    poster_keyboard,
    skip_keyboard,
    use_code_keyboard,
)
from bot.states import AddMovie, EditMovie
from bot.texts import parse_add_args, parse_code, parse_extra, t
from bot.utils import extract_photo

logger = logging.getLogger(__name__)
router = Router(name="admin_movies")

PAGE_SIZE = 10
MAX_CODE = 1_000_000_000


def _dash(lang: str, value: object | None) -> str:
    if value is None or value == "":
        return t(lang, "dash")
    return str(value)


def _edit_text(lang: str, movie: Movie) -> str:
    return t(
        lang,
        "edit_menu",
        code=movie.code,
        title=movie.title,
        year=_dash(lang, movie.year),
        genre=_dash(lang, movie.genre),
        description=_dash(lang, movie.description),
        poster=t(lang, "poster_yes" if movie.poster_file_id else "poster_no"),
        views=movie.views,
    )


def _preferred_code(data: dict, db: Database) -> int | None:
    preferred = data.get("preferred_code")
    if preferred and not db.code_exists(int(preferred)):
        return int(preferred)
    return None


# ---- /add ----

@router.message(Command("add"))
async def cmd_add(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    config: Config,
    db: Database,
    is_admin: bool,
    lang: str,
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    await state.clear()
    code, title = parse_add_args(command.args)
    if code is not None and code > MAX_CODE:
        await message.answer(t(lang, "add_invalid_code"))
        return
    if code is not None and db.code_exists(code) and not title:
        await message.answer(t(lang, "add_code_taken", code=code))
        return
    if code is not None:
        await state.update_data(preferred_code=code)
    if title:
        await state.update_data(title=title)
        await state.set_state(AddMovie.waiting_extra)
        await message.answer(
            t(lang, "add_ask_extra", title=title),
            reply_markup=skip_keyboard(lang, "add:skip_extra"),
        )
        return
    await state.set_state(AddMovie.waiting_title)
    await message.answer(t(lang, "add_ask_title"))


@router.message(StateFilter(AddMovie.waiting_title), F.text, ~F.text.startswith("/"))
async def add_got_title(message: Message, state: FSMContext, lang: str) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(t(lang, "add_invalid_title"))
        return
    await state.update_data(title=title)
    await state.set_state(AddMovie.waiting_extra)
    await message.answer(
        t(lang, "add_ask_extra", title=title),
        reply_markup=skip_keyboard(lang, "add:skip_extra"),
    )


@router.message(StateFilter(AddMovie.waiting_title))
async def add_need_title(message: Message, lang: str) -> None:
    await message.answer(t(lang, "add_invalid_title"))


async def _ask_poster(message: Message, state: FSMContext, lang: str) -> None:
    await state.set_state(AddMovie.waiting_poster)
    await message.answer(
        t(lang, "add_ask_poster"),
        reply_markup=poster_keyboard(lang, skip_callback="add:skip_poster"),
    )


async def _ask_code_or_save(
    message: Message, state: FSMContext, db: Database, lang: str, user_id: int | None
) -> None:
    data = await state.get_data()
    preferred = _preferred_code(data, db)
    if preferred is not None:
        await _save_movie(
            message=message,
            state=state,
            db=db,
            lang=lang,
            user_id=user_id,
            code=preferred,
        )
        return
    # Если указанный код уже занят — предложим свободный.
    code = db.next_free_code()
    await state.set_state(AddMovie.waiting_code)
    hint = t(lang, "add_ask_code", code=code)
    if data.get("preferred_code") and db.code_exists(int(data["preferred_code"])):
        hint = t(lang, "add_code_taken", code=int(data["preferred_code"])) + "\n\n" + hint
    await message.answer(hint, reply_markup=use_code_keyboard(lang, code))


@router.callback_query(StateFilter(AddMovie.waiting_extra), F.data == "add:skip_extra")
async def add_skip_extra(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    await state.update_data(year=None, genre=None, description=None)
    await callback.answer()
    if callback.message:
        await _ask_poster(callback.message, state, lang)


@router.message(StateFilter(AddMovie.waiting_extra), F.text, ~F.text.startswith("/"))
async def add_got_extra(message: Message, state: FSMContext, lang: str) -> None:
    try:
        extra = parse_extra(message.text or "")
    except ValueError:
        await message.answer(t(lang, "invalid_year"))
        return
    await state.update_data(**extra)
    await _ask_poster(message, state, lang)


@router.callback_query(StateFilter(AddMovie.waiting_poster), F.data == "add:skip_poster")
async def add_skip_poster(
    callback: CallbackQuery, state: FSMContext, db: Database, lang: str
) -> None:
    await state.update_data(poster_file_id=None)
    await callback.answer()
    if callback.message:
        uid = callback.from_user.id if callback.from_user else None
        await _ask_code_or_save(callback.message, state, db, lang, uid)


@router.message(StateFilter(AddMovie.waiting_poster), F.photo | F.document)
async def add_got_poster(
    message: Message, state: FSMContext, db: Database, lang: str
) -> None:
    poster = extract_photo(message)
    if not poster:
        await message.answer(t(lang, "need_photo"))
        return
    await state.update_data(poster_file_id=poster)
    uid = message.from_user.id if message.from_user else None
    await _ask_code_or_save(message, state, db, lang, uid)


@router.message(StateFilter(AddMovie.waiting_poster))
async def add_need_poster(message: Message, lang: str) -> None:
    await message.answer(t(lang, "need_photo"))


async def _save_movie(
    *,
    message: Message,
    state: FSMContext,
    db: Database,
    lang: str,
    user_id: int | None,
    code: int,
) -> None:
    data = await state.get_data()
    title = data.get("title")
    if not title:
        await state.clear()
        await message.answer(t(lang, "add_no_title"))
        return
    if db.code_exists(code):
        await message.answer(
            t(lang, "add_code_taken", code=code),
            reply_markup=use_code_keyboard(lang, db.next_free_code()),
        )
        await state.set_state(AddMovie.waiting_code)
        return
    try:
        movie = db.add_movie(
            code=code,
            title=title,
            poster_file_id=data.get("poster_file_id"),
            description=data.get("description"),
            year=data.get("year"),
            genre=data.get("genre"),
            created_by=user_id,
        )
    except ValueError as exc:
        await message.answer(t(lang, "add_failed", error=str(exc)))
        return
    await state.clear()
    await message.answer(t(lang, "add_done", title=movie.title, code=movie.code))


@router.callback_query(StateFilter(AddMovie.waiting_code), F.data.startswith("usecode:"))
async def add_use_code(
    callback: CallbackQuery, state: FSMContext, db: Database, lang: str
) -> None:
    if not callback.data:
        await callback.answer()
        return
    try:
        code = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    await callback.answer()
    if callback.message:
        await _save_movie(
            message=callback.message,
            state=state,
            db=db,
            lang=lang,
            user_id=callback.from_user.id if callback.from_user else None,
            code=code,
        )


@router.message(StateFilter(AddMovie.waiting_code), F.text, ~F.text.startswith("/"))
async def add_custom_code(
    message: Message, state: FSMContext, db: Database, lang: str
) -> None:
    code = parse_code(message.text or "")
    if code is None or code > MAX_CODE:
        await message.answer(t(lang, "add_invalid_code"))
        return
    await _save_movie(
        message=message,
        state=state,
        db=db,
        lang=lang,
        user_id=message.from_user.id if message.from_user else None,
        code=code,
    )


# ---- /del ----

@router.message(Command("del", "delete"))
async def cmd_del(
    message: Message,
    command: CommandObject,
    config: Config,
    db: Database,
    is_admin: bool,
    lang: str,
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    code = parse_code(command.args or "")
    if code is None:
        await message.answer(t(lang, "del_usage"))
        return
    movie = db.get_movie_by_code(code)
    if not movie:
        await message.answer(t(lang, "del_not_found", code=code))
        return
    await message.answer(
        t(lang, "del_confirm", title=movie.title, code=movie.code),
        reply_markup=confirm_delete_keyboard(lang, movie.code),
    )


@router.callback_query(F.data.startswith("del:"))
async def cb_delete(callback: CallbackQuery, config: Config, db: Database, lang: str, is_admin: bool) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return
    try:
        code = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    deleted = db.delete_movie(code)
    await callback.answer()
    text = t(lang, "del_done", code=code) if deleted else t(lang, "del_not_found", code=code)
    if callback.message:
        await callback.message.edit_text(text)


# ---- /edit ----

@router.message(Command("edit"))
async def cmd_edit(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    config: Config,
    db: Database,
    is_admin: bool,
    lang: str,
) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    code = parse_code(command.args or "")
    if code is None:
        await message.answer(t(lang, "edit_usage"))
        return
    movie = db.get_movie_by_code(code)
    if not movie:
        await message.answer(t(lang, "edit_not_found", code=code))
        return
    await state.clear()
    await state.update_data(edit_code=movie.code)
    await message.answer(_edit_text(lang, movie), reply_markup=edit_menu_keyboard(lang, movie.code))


@router.callback_query(F.data.startswith("edit:"), ~F.data.startswith("edit:clear_"))
async def cb_edit_field(
    callback: CallbackQuery, state: FSMContext, config: Config, db: Database, lang: str,
    is_admin: bool
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    _, code_s, field = parts
    try:
        code = int(code_s)
    except ValueError:
        await callback.answer()
        return
    if field not in {"title", "year", "genre", "description", "code", "poster"}:
        await callback.answer()
        return
    movie = db.get_movie_by_code(code)
    if not movie:
        await callback.answer(t(lang, "edit_not_found", code=code), show_alert=True)
        return
    await state.update_data(edit_code=code, edit_field=field)
    await callback.answer()
    prompts = {
        "title": "edit_ask_title",
        "year": "edit_ask_year",
        "genre": "edit_ask_genre",
        "description": "edit_ask_description",
        "code": "edit_ask_code",
        "poster": "edit_ask_poster",
    }
    if field == "poster":
        await state.set_state(EditMovie.waiting_poster)
        if callback.message:
            await callback.message.answer(
                t(lang, prompts[field]),
                reply_markup=poster_keyboard(
                    lang, can_clear=True, skip_callback="cancel"
                ),
            )
        return
    await state.set_state(EditMovie.waiting_value)
    if callback.message:
        await callback.message.answer(t(lang, prompts[field]))


async def _refresh_edit(message: Message, db: Database, lang: str, code: int) -> None:
    movie = db.get_movie_by_code(code)
    if not movie:
        await message.answer(t(lang, "edit_not_found", code=code))
        return
    await message.answer(_edit_text(lang, movie), reply_markup=edit_menu_keyboard(lang, movie.code))


@router.callback_query(StateFilter(EditMovie.waiting_poster), F.data == "edit:clear_poster")
async def edit_clear_poster(
    callback: CallbackQuery, state: FSMContext, db: Database, lang: str
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    if not code:
        await state.clear()
        await callback.answer()
        return
    db.update_movie(int(code), poster_file_id=None)
    await state.set_state(None)
    await state.update_data(edit_field=None)
    await callback.answer(t(lang, "edit_poster_cleared"))
    if callback.message:
        await callback.message.answer(t(lang, "edit_done"))
        await _refresh_edit(callback.message, db, lang, int(code))


@router.message(StateFilter(EditMovie.waiting_poster), F.photo | F.document)
async def edit_got_poster(
    message: Message, state: FSMContext, db: Database, lang: str
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    poster = extract_photo(message)
    if not poster or not code:
        await message.answer(t(lang, "need_photo"))
        return
    db.update_movie(int(code), poster_file_id=poster)
    await state.set_state(None)
    await state.update_data(edit_field=None)
    await message.answer(t(lang, "edit_done"))
    await _refresh_edit(message, db, lang, int(code))


@router.message(StateFilter(EditMovie.waiting_poster))
async def edit_need_poster(message: Message, lang: str) -> None:
    await message.answer(t(lang, "need_photo"))


@router.message(StateFilter(EditMovie.waiting_value), F.text, ~F.text.startswith("/"))
async def edit_got_value(
    message: Message, state: FSMContext, db: Database, lang: str
) -> None:
    data = await state.get_data()
    code = data.get("edit_code")
    field = data.get("edit_field")
    if not code or not field:
        await state.clear()
        await message.answer(t(lang, "cancelled"))
        return
    raw = (message.text or "").strip()
    updates: dict = {}
    if field == "title":
        if not raw or raw.startswith("/"):
            await message.answer(t(lang, "add_invalid_title"))
            return
        updates["title"] = raw
    elif field == "year":
        if raw in {"-", "—", "–"}:
            updates["year"] = None
        elif raw.isdigit() and 1800 <= int(raw) <= 2100:
            updates["year"] = int(raw)
        else:
            await message.answer(t(lang, "invalid_year"))
            return
    elif field in {"genre", "description"}:
        updates[field] = None if raw in {"-", "—", "–"} else raw
    elif field == "code":
        new_code = parse_code(raw)
        if new_code is None or new_code > MAX_CODE:
            await message.answer(t(lang, "add_invalid_code"))
            return
        if new_code != int(code) and db.code_exists(new_code):
            await message.answer(t(lang, "edit_code_taken", code=new_code))
            return
        updates["code"] = new_code
    else:
        await state.clear()
        return
    try:
        movie = db.update_movie(int(code), **updates)
    except ValueError as exc:
        await message.answer(t(lang, "add_failed", error=str(exc)))
        return
    await state.set_state(None)
    await state.update_data(edit_field=None, edit_code=movie.code if movie else code)
    await message.answer(t(lang, "edit_done"))
    if movie:
        await _refresh_edit(message, db, lang, movie.code)


# ---- /list ----

def _list_page(db: Database, lang: str, page: int) -> tuple[str, int, int]:
    total = db.count_movies()
    pages = max(1, math.ceil(total / PAGE_SIZE)) if total else 1
    page = max(1, min(page, pages))
    movies, _ = db.list_movies(offset=(page - 1) * PAGE_SIZE, limit=PAGE_SIZE)
    if not movies:
        return t(lang, "list_empty"), page, pages
    lines = [t(lang, "list_title", page=page, pages=pages, total=total)]
    for movie in movies:
        lines.append(
            t(lang, "list_line", code=movie.code, title=movie.title, views=movie.views)
        )
    return "\n".join(lines), page, pages


@router.message(Command("list"))
async def cmd_list(message: Message, config: Config, db: Database, lang: str, is_admin: bool) -> None:
    if not is_admin:
        await message.answer(t(lang, "admin_only"))
        return
    text, page, pages = _list_page(db, lang, 1)
    await message.answer(text, reply_markup=list_keyboard(lang, page, pages))


@router.callback_query(F.data.startswith("list:"))
async def cb_list(callback: CallbackQuery, config: Config, db: Database, lang: str, is_admin: bool) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    if not callback.data:
        await callback.answer()
        return
    try:
        page = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer()
        return
    text, page, pages = _list_page(db, lang, page)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=list_keyboard(lang, page, pages))


@router.callback_query(F.data == "panel:list")
async def cb_panel_list(
    callback: CallbackQuery, is_admin: bool, db: Database, lang: str
) -> None:
    if not is_admin:
        await callback.answer(t(lang, "admin_only"), show_alert=True)
        return
    text, page, pages = _list_page(db, lang, 1)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(text, reply_markup=list_keyboard(lang, page, pages))
