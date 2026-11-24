"""Поиск фильма по коду, топ-10, проверка подписки."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from bot.db import Database, Movie
from bot.keyboards import subscription_keyboard
from bot.texts import format_movie_text, parse_code, t
from bot.utils import missing_channels

logger = logging.getLogger(__name__)

router = Router(name="user")


async def send_movie_info(message: Message, movie: Movie, lang: str, views: int) -> None:
    """Отправляет карточку фильма текстом или фото+подпись, без видео."""
    text = format_movie_text(lang, movie, views=views, include_views=False)
    if movie.poster_file_id:
        caption = format_movie_text(
            lang, movie, views=views, include_views=False, limit=1024
        )
        try:
            await message.answer_photo(photo=movie.poster_file_id, caption=caption)
            return
        except TelegramAPIError as exc:
            logger.warning("Failed to send poster for code %s: %s", movie.code, exc)
    await message.answer(text)


@router.message(Command("top"))
async def cmd_top(message: Message, db: Database, lang: str) -> None:
    movies = db.top_movies(10)
    if not movies:
        await message.answer(t(lang, "top_empty"))
        return
    lines = [t(lang, "top_title", n=len(movies))]
    for i, movie in enumerate(movies, start=1):
        lines.append(
            t(
                lang,
                "top_line",
                i=i,
                code=movie.code,
                views=movie.views,
            )
        )
    await message.answer("\n".join(lines))


@router.callback_query(F.data == "checksub")
async def cb_check_sub(callback: CallbackQuery, db: Database, lang: str) -> None:
    if not callback.from_user:
        await callback.answer()
        return
    missing = await missing_channels(callback.bot, db, callback.from_user.id)
    if missing:
        await callback.answer(t(lang, "sub_still_missing"), show_alert=True)
        return
    await callback.answer()
    if callback.message:
        await callback.message.answer(t(lang, "sub_ok"))


@router.callback_query(F.data.startswith("chinfo:"))
async def cb_channel_info(callback: CallbackQuery, lang: str) -> None:
    # Канал без публичной ссылки — пользователь должен найти его сам / админ задаст url.
    await callback.answer(t(lang, "sub_required"), show_alert=True)


@router.message(StateFilter(default_state), F.text, F.text.regexp(r"^\s*\d+\s*$"))
async def on_code(message: Message, db: Database, lang: str, state: FSMContext) -> None:
    # На всякий случай: если состояние всё же есть, не перехватываем ввод админа.
    if await state.get_state():
        return
    code = parse_code(message.text or "")
    if code is None:
        await message.answer(t(lang, "send_code_hint"))
        return
    user_id = message.from_user.id if message.from_user else None
    movie = db.get_movie_by_code(code)
    db.log_search(user_id, code, found=movie is not None)
    if movie is None:
        await message.answer(t(lang, "movie_not_found", code=code))
        return
    if user_id:
        missing = await missing_channels(message.bot, db, user_id)
        if missing:
            await message.answer(
                t(lang, "sub_required"),
                reply_markup=subscription_keyboard(lang, missing),
            )
            return
    views = db.increment_views(movie.code)
    await send_movie_info(message, movie, lang, views)


@router.message(StateFilter(default_state), F.text, ~F.text.startswith("/"))
async def on_other_text(message: Message, lang: str) -> None:
    await message.answer(t(lang, "send_code_hint"))
