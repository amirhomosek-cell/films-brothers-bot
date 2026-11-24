"""Загрузка настроек из .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "bot.db"


@dataclass(frozen=True)
class RequiredChannel:
    """Канал обязательной подписки, заданный через REQUIRED_CHANNELS."""

    chat_id: str
    title: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    db_path: Path
    port: int | None = None
    required_channels: tuple[RequiredChannel, ...] = ()

    def is_owner(self, user_id: int | None) -> bool:
        """Главный администратор из ADMIN_IDS. Полная проверка прав — bot.access.is_admin."""
        return user_id is not None and user_id in self.admin_ids

    def is_admin(self, user_id: int | None) -> bool:
        """Только главные админы из .env (без таблицы admins). Используйте bot.access.is_admin."""
        return self.is_owner(user_id)


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            raise ValueError(
                f"Некорректный ADMIN_IDS: «{part}». Укажите числовые Telegram ID через запятую."
            ) from None
    return frozenset(ids)


def parse_required_channels(raw: str) -> tuple[RequiredChannel, ...]:
    """Разбирает REQUIRED_CHANNELS: chat_id или chat_id:@username / chat_id:https://...

    Несколько записей через запятую или точку с запятой.
    Пример: -1003834817665:@musordrop14886752
    """
    channels: list[RequiredChannel] = []
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        chat_id, sep, rest = part.partition(":")
        chat_id = chat_id.strip()
        if not chat_id:
            raise ValueError(
                "Некорректный REQUIRED_CHANNELS: пустой chat_id. "
                "Пример: -100123456:@channelusername"
            )
        rest = rest.strip() if sep else ""
        title: str | None = None
        url: str | None = None
        if rest:
            if rest.startswith("http://") or rest.startswith("https://"):
                url = rest
                if "t.me/" in rest:
                    slug = rest.rsplit("t.me/", 1)[-1].split("?", 1)[0].strip("/")
                    if slug and not slug.startswith("+"):
                        title = slug
            else:
                slug = rest.lstrip("@")
                title = slug or None
                url = f"https://t.me/{slug}" if slug else None
        channels.append(RequiredChannel(chat_id=chat_id, title=title, url=url))
    return tuple(channels)


def _parse_port(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        port = int(raw)
    except ValueError:
        raise ValueError(f"Некорректный PORT: «{raw}». Укажите целое число.") from None
    if not (1 <= port <= 65535):
        raise ValueError(f"Некорректный PORT: {port}. Ожидается число от 1 до 65535.")
    return port


def load_config(*, require_token: bool = True) -> Config:
    """Читает .env из корня проекта. Без токена можно вызывать только для тестов."""
    load_dotenv(ROOT_DIR / ".env")
    token = (os.getenv("BOT_TOKEN") or "").strip()
    if require_token and not token:
        raise SystemExit(
            "Не указан BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен от @BotFather."
        )
    raw_admins = os.getenv("ADMIN_IDS") or ""
    admin_ids = _parse_admin_ids(raw_admins)
    if require_token and not admin_ids:
        raise SystemExit(
            "Не указан ADMIN_IDS. Добавьте свой Telegram ID в .env (узнать: @userinfobot)."
        )
    db_raw = (os.getenv("DB_PATH") or "").strip()
    db_path = Path(db_raw) if db_raw else DEFAULT_DB_PATH
    if not db_path.is_absolute():
        db_path = ROOT_DIR / db_path
    port = _parse_port(os.getenv("PORT") or "")
    required_channels = parse_required_channels(os.getenv("REQUIRED_CHANNELS") or "")
    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        db_path=db_path,
        port=port,
        required_channels=required_channels,
    )
