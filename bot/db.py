"""Слой работы с SQLite: пользователи, фильмы, каналы, настройки, статистика."""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from bot.config import RequiredChannel

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Movie:
    id: int
    code: int
    title: str
    description: str | None
    year: int | None
    genre: str | None
    poster_file_id: str | None
    views: int
    created_at: str
    created_by: int | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Movie":
        keys = set(row.keys())
        poster = None
        if "poster_file_id" in keys:
            poster = row["poster_file_id"]
        return cls(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            description=row["description"],
            year=row["year"],
            genre=row["genre"],
            poster_file_id=poster,
            views=row["views"],
            created_at=row["created_at"],
            created_by=row["created_by"],
        )


@dataclass
class Channel:
    id: int
    chat_id: str
    title: str | None
    url: str | None
    added_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Channel":
        return cls(
            id=row["id"],
            chat_id=row["chat_id"],
            title=row["title"],
            url=row["url"],
            added_at=row["added_at"],
        )


@dataclass
class AdminInfo:
    user_id: int
    is_owner: bool
    username: str | None
    first_name: str | None
    added_by: int | None
    added_at: str | None


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            isolation_level=None,  # autocommit; транзакции — явно
        )
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_schema(self) -> None:
        cur = self._conn
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'ru',
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                year INTEGER,
                genre TEXT,
                poster_file_id TEXT,
                views INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by INTEGER
            );

            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL UNIQUE,
                title TEXT,
                url TEXT,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                code INTEGER,
                found INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT NOT NULL,
                username TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_movies_views ON movies(views DESC);
            CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at);
            """
        )
        # подписка включена по умолчанию, если каналы заданы; флаг хранится отдельно
        cur.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES('subscription_enabled', '1')"
        )
        self._migrate_movies_table()


    def _migrate_movies_table(self) -> None:
        """Пересобирает movies, если схема старая (file_id NOT NULL, нет poster_file_id).

        Вызывать только при уже взятом self._lock (из _init_schema).
        """
        cols = list(self._conn.execute("PRAGMA table_info(movies)"))
        if not cols:
            return
        names = [c[1] for c in cols]
        file_id_notnull = any(c[1] == "file_id" and c[3] for c in cols)
        already_new = "poster_file_id" in names and "file_id" not in names
        if already_new and not file_id_notnull:
            return
        logger.info("Миграция таблицы movies: file_id → poster_file_id (nullable)")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                """
                CREATE TABLE movies_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code INTEGER NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT,
                    year INTEGER,
                    genre TEXT,
                    poster_file_id TEXT,
                    views INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    created_by INTEGER
                )
                """
            )
            # Старые file_id были видео, в постер их не переносим.
            if "poster_file_id" in names:
                poster_expr = "poster_file_id"
            else:
                poster_expr = "NULL"
            self._conn.execute(
                f"""
                INSERT INTO movies_new(
                    id, code, title, description, year, genre,
                    poster_file_id, views, created_at, created_by
                )
                SELECT
                    id, code, title, description, year, genre,
                    {poster_expr}, views, created_at, created_by
                FROM movies
                """
            )
            self._conn.execute("DROP TABLE movies")
            self._conn.execute("ALTER TABLE movies_new RENAME TO movies")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_movies_views ON movies(views DESC)"
            )
            self._conn.execute("COMMIT")
        except Exception:
            try:
                self._conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        logger.info("Миграция таблицы movies завершена")

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, tuple(params))

    def executemany(self, sql: str, seq: Iterable[Iterable[Any]]) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.executemany(sql, list(seq))

    # --- users ---

    def upsert_user(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> None:
        now = _now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO users(user_id, language, username, first_name, created_at, last_seen)
                VALUES(?, 'ru', ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_seen = excluded.last_seen
                """,
                (user_id, username, first_name, now, now),
            )

    def set_language(self, user_id: int, language: str) -> None:
        if language not in {"ru", "uz"}:
            raise ValueError(f"Unsupported language: {language}")
        now = _now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO users(user_id, language, created_at, last_seen)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
                """,
                (user_id, language, now, now),
            )

    def get_language(self, user_id: int | None) -> str:
        if user_id is None:
            return "ru"
        row = self.execute(
            "SELECT language FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return "ru"
        lang = row["language"]
        return lang if lang in {"ru", "uz"} else "ru"

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        return self.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def count_users(self) -> int:
        return int(self.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"])

    def all_user_ids(self) -> list[int]:
        rows = self.execute("SELECT user_id FROM users ORDER BY user_id").fetchall()
        return [int(r["user_id"]) for r in rows]

    # --- movies ---

    def next_free_code(self) -> int:
        """Минимальный свободный положительный код (удалённые коды используются снова)."""
        rows = self.execute("SELECT code FROM movies ORDER BY code").fetchall()
        expected = 1
        for row in rows:
            code = int(row["code"])
            if code == expected:
                expected += 1
            elif code > expected:
                break
        return expected

    def code_exists(self, code: int) -> bool:
        row = self.execute("SELECT 1 FROM movies WHERE code = ?", (code,)).fetchone()
        return row is not None

    def add_movie(
        self,
        *,
        code: int,
        title: str,
        poster_file_id: str | None = None,
        description: str | None = None,
        year: int | None = None,
        genre: str | None = None,
        created_by: int | None = None,
    ) -> Movie:
        title = (title or "").strip()
        if not title:
            raise ValueError("title is required")
        if code < 1:
            raise ValueError("code must be a positive integer")
        description = (description or "").strip() or None
        genre = (genre or "").strip() or None
        poster_file_id = (poster_file_id or "").strip() or None
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                exists = self._conn.execute(
                    "SELECT 1 FROM movies WHERE code = ?", (code,)
                ).fetchone()
                if exists:
                    self._conn.execute("ROLLBACK")
                    raise ValueError(f"code {code} already exists")
                cur = self._conn.execute(
                    """
                    INSERT INTO movies(
                        code, title, description, year, genre,
                        poster_file_id, views, created_at, created_by
                    ) VALUES(?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        code,
                        title,
                        description,
                        year,
                        genre,
                        poster_file_id,
                        _now(),
                        created_by,
                    ),
                )
                self._conn.execute("COMMIT")
                movie_id = int(cur.lastrowid)
            except ValueError:
                raise
            except Exception:
                try:
                    self._conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
        movie = self.get_movie_by_code(code)
        assert movie is not None
        assert movie.id == movie_id
        return movie

    def get_movie_by_code(self, code: int) -> Movie | None:
        row = self.execute("SELECT * FROM movies WHERE code = ?", (code,)).fetchone()
        return Movie.from_row(row) if row else None

    def delete_movie(self, code: int) -> bool:
        cur = self.execute("DELETE FROM movies WHERE code = ?", (code,))
        return cur.rowcount > 0

    def update_movie(self, current_code: int, **fields: Any) -> Movie | None:
        allowed = {
            "title",
            "description",
            "year",
            "genre",
            "poster_file_id",
            "code",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_movie_by_code(current_code)
        if "title" in updates:
            title = (updates["title"] or "").strip()
            if not title:
                raise ValueError("title is required")
            updates["title"] = title
        if "description" in updates:
            desc = updates["description"]
            updates["description"] = (desc or "").strip() or None
        if "genre" in updates:
            genre = updates["genre"]
            updates["genre"] = (genre or "").strip() or None
        if "poster_file_id" in updates:
            poster = updates["poster_file_id"]
            updates["poster_file_id"] = (poster or "").strip() or None
        if "code" in updates:
            new_code = int(updates["code"])
            if new_code < 1:
                raise ValueError("code must be a positive integer")
            if new_code != current_code and self.code_exists(new_code):
                raise ValueError(f"code {new_code} already exists")
        assignments = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [current_code]
        self.execute(f"UPDATE movies SET {assignments} WHERE code = ?", values)
        return self.get_movie_by_code(int(updates.get("code", current_code)))

    def increment_views(self, code: int) -> int:
        with self._lock:
            self._conn.execute(
                "UPDATE movies SET views = views + 1 WHERE code = ?", (code,)
            )
            row = self._conn.execute(
                "SELECT views FROM movies WHERE code = ?", (code,)
            ).fetchone()
        return int(row["views"]) if row else 0

    def list_movies(self, offset: int = 0, limit: int = 10) -> tuple[list[Movie], int]:
        if offset < 0:
            offset = 0
        if limit < 1:
            limit = 10
        total = int(self.execute("SELECT COUNT(*) AS n FROM movies").fetchone()["n"])
        rows = self.execute(
            "SELECT * FROM movies ORDER BY code LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [Movie.from_row(r) for r in rows], total

    def top_movies(self, limit: int = 10) -> list[Movie]:
        rows = self.execute(
            "SELECT * FROM movies ORDER BY views DESC, code ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [Movie.from_row(r) for r in rows]

    def count_movies(self) -> int:
        return int(self.execute("SELECT COUNT(*) AS n FROM movies").fetchone()["n"])

    # --- searches / stats ---

    def log_search(self, user_id: int | None, code: int, found: bool) -> None:
        self.execute(
            "INSERT INTO searches(user_id, code, found, created_at) VALUES(?, ?, ?, ?)",
            (user_id, code, 1 if found else 0, _now()),
        )

    def count_searches(self, *, found_only: bool = False) -> int:
        if found_only:
            sql = "SELECT COUNT(*) AS n FROM searches WHERE found = 1"
        else:
            sql = "SELECT COUNT(*) AS n FROM searches"
        return int(self.execute(sql).fetchone()["n"])

    def stats(self) -> dict[str, int]:
        return {
            "users": self.count_users(),
            "movies": self.count_movies(),
            "searches": self.count_searches(),
            "found": self.count_searches(found_only=True),
            "total_views": int(
                self.execute("SELECT COALESCE(SUM(views), 0) AS n FROM movies").fetchone()["n"]
            ),
        }

    # --- channels ---

    def add_channel(self, chat_id: str, title: str | None = None, url: str | None = None) -> Channel:
        chat_id = str(chat_id).strip()
        if not chat_id:
            raise ValueError("chat_id is required")
        with self._lock:
            try:
                cur = self._conn.execute(
                    """
                    INSERT INTO channels(chat_id, title, url, added_at)
                    VALUES(?, ?, ?, ?)
                    """,
                    (chat_id, (title or "").strip() or None, (url or "").strip() or None, _now()),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"channel {chat_id} already exists") from exc
            channel_id = int(cur.lastrowid)
        channel = self.get_channel(channel_id)
        assert channel is not None
        return channel

    def get_channel(self, channel_id: int) -> Channel | None:
        row = self.execute("SELECT * FROM channels WHERE id = ?", (channel_id,)).fetchone()
        return Channel.from_row(row) if row else None

    def get_channel_by_chat_id(self, chat_id: str) -> Channel | None:
        row = self.execute(
            "SELECT * FROM channels WHERE chat_id = ?", (str(chat_id).strip(),)
        ).fetchone()
        return Channel.from_row(row) if row else None

    def remove_channel(self, channel_id: int) -> bool:
        cur = self.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        return cur.rowcount > 0

    def list_channels(self) -> list[Channel]:
        rows = self.execute("SELECT * FROM channels ORDER BY id").fetchall()
        return [Channel.from_row(r) for r in rows]

    # --- settings ---

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def subscription_enabled(self) -> bool:
        return self.get_setting("subscription_enabled", "1") == "1"

    def set_subscription_enabled(self, enabled: bool) -> None:
        self.set_setting("subscription_enabled", "1" if enabled else "0")


    def seed_required_channels(self, channels: Iterable[RequiredChannel]) -> int:
        """Добавляет каналы из REQUIRED_CHANNELS, только если chat_id ещё нет в базе."""
        added = 0
        for channel in channels:
            chat_id = (channel.chat_id or "").strip()
            if not chat_id:
                continue
            if self.get_channel_by_chat_id(chat_id):
                continue
            self.add_channel(chat_id, title=channel.title, url=channel.url)
            added += 1
            logger.info("Добавлен канал из REQUIRED_CHANNELS: %s", chat_id)
        return added

    def subscription_required(self) -> bool:
        """Проверять подписку, только если флаг включён и есть хотя бы один канал."""
        return self.subscription_enabled() and bool(self.list_channels())


    def find_user_by_username(self, username: str) -> sqlite3.Row | None:
        name = (username or "").lstrip("@").strip()
        if not name:
            return None
        return self.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (name,),
        ).fetchone()

    # --- admins ---

    def is_db_admin(self, user_id: int) -> bool:
        row = self.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is not None

    def add_admin(
        self,
        user_id: int,
        added_by: int | None = None,
        username: str | None = None,
    ) -> AdminInfo:
        if user_id < 1:
            raise ValueError("user_id must be a positive integer")
        username = (username or "").lstrip("@").strip() or None
        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO admins(user_id, added_by, added_at, username)
                    VALUES(?, ?, ?, ?)
                    """,
                    (user_id, added_by, _now(), username),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"admin {user_id} already exists") from exc
        listed = {a.user_id: a for a in self.list_admins(owner_ids=())}
        info = listed.get(user_id)
        if info is not None:
            return info
        user = self.get_user(user_id)
        return AdminInfo(
            user_id=user_id,
            is_owner=False,
            username=(user["username"] if user else None) or username,
            first_name=user["first_name"] if user else None,
            added_by=added_by,
            added_at=_now(),
        )

    def remove_db_admin(self, user_id: int) -> bool:
        cur = self.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        return cur.rowcount > 0

    def list_admins(self, owner_ids: Iterable[int] = ()) -> list[AdminInfo]:
        """Главные админы из owner_ids и дополнительные из таблицы admins, без дублей."""
        result: dict[int, AdminInfo] = {}
        for oid in sorted({int(x) for x in owner_ids}):
            user = self.get_user(oid)
            result[oid] = AdminInfo(
                user_id=oid,
                is_owner=True,
                username=user["username"] if user else None,
                first_name=user["first_name"] if user else None,
                added_by=None,
                added_at=None,
            )
        rows = self.execute(
            """
            SELECT a.user_id, a.added_by, a.added_at, a.username AS snap_username,
                   u.username, u.first_name
            FROM admins a
            LEFT JOIN users u ON u.user_id = a.user_id
            ORDER BY a.added_at
            """
        ).fetchall()
        for row in rows:
            uid = int(row["user_id"])
            username = row["username"] or row["snap_username"]
            first_name = row["first_name"]
            if uid in result:
                current = result[uid]
                result[uid] = AdminInfo(
                    user_id=uid,
                    is_owner=True,
                    username=current.username or username,
                    first_name=current.first_name or first_name,
                    added_by=row["added_by"],
                    added_at=row["added_at"],
                )
                continue
            result[uid] = AdminInfo(
                user_id=uid,
                is_owner=False,
                username=username,
                first_name=first_name,
                added_by=row["added_by"],
                added_at=row["added_at"],
            )
        return sorted(result.values(), key=lambda a: (not a.is_owner, a.user_id))

