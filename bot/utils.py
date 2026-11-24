"""Вспомогательные функции без зависимости от запущенного бота."""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Document, Message, PhotoSize, Video

from bot.db import Channel, Database

# Статусы, при которых пользователь считается подписанным.
_SUBSCRIBED = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
}


def extract_video(message: Message) -> tuple[str, str | None] | None:
    """Возвращает (file_id, file_unique_id) из видео или видео-документа.

    Поддерживается и обычная отправка, и пересланный пост из канала.
    """
    video: Video | None = message.video
    if video:
        return video.file_id, video.file_unique_id
    document: Document | None = message.document
    if document and document.mime_type and document.mime_type.startswith("video/"):
        return document.file_id, document.file_unique_id
    return None


def extract_photo(message: Message) -> str | None:
    """file_id самого большого фото в сообщении (в том числе пересланного)."""
    photos: list[PhotoSize] | None = message.photo
    if photos:
        return photos[-1].file_id
    document = message.document
    if document and document.mime_type and document.mime_type.startswith("image/"):
        return document.file_id
    return None


def _channel_chat_target(chat_id: str) -> int | str:
    raw = chat_id.strip()
    if raw.startswith("@"):
        return raw
    try:
        return int(raw)
    except ValueError:
        return raw


async def is_subscribed(bot: Bot, chat_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(_channel_chat_target(chat_id), user_id)
    except (TelegramBadRequest, TelegramForbiddenError, TelegramAPIError):
        return False
    return member.status in _SUBSCRIBED


async def missing_channels(bot: Bot, db: Database, user_id: int) -> list[Channel]:
    if not db.subscription_required():
        return []
    missing: list[Channel] = []
    for channel in db.list_channels():
        if not await is_subscribed(bot, channel.chat_id, user_id):
            missing.append(channel)
    return missing


def parse_channel_ref(text: str) -> str | None:
    """Нормализует @username или числовой id канала."""
    raw = (text or "").strip()
    if not raw:
        return None
    if raw.startswith("https://t.me/") or raw.startswith("http://t.me/"):
        raw = raw.split("t.me/", 1)[1]
        raw = raw.split("?")[0].strip("/")
        if raw.startswith("+"):
            # Приватная invite-ссылка без username — нужен числовой id.
            return None
        raw = "@" + raw if not raw.startswith("@") else raw
    if raw.startswith("@"):
        name = raw[1:]
        if name.replace("_", "").isalnum() and name:
            return "@" + name
        return None
    if raw.lstrip("-").isdigit():
        return raw
    return None
