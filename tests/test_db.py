"""Автономные тесты слоя базы данных. Telegram не нужен."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.db import Database, AdminInfo


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "test.db")

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def _add(self, code: int = 1, title: str = "Matrix", **kwargs):
        if "file_id" in kwargs:
            kwargs["poster_file_id"] = kwargs.pop("file_id")
        return self.db.add_movie(code=code, title=title, **kwargs)

    def test_default_language_is_russian(self) -> None:
        self.assertEqual(self.db.get_language(999), "ru")
        self.db.upsert_user(1, "ivan", "Ivan")
        self.assertEqual(self.db.get_language(1), "ru")

    def test_set_language(self) -> None:
        self.db.set_language(5, "uz")
        self.assertEqual(self.db.get_language(5), "uz")
        self.db.set_language(5, "ru")
        self.assertEqual(self.db.get_language(5), "ru")
        with self.assertRaises(ValueError):
            self.db.set_language(5, "en")

    def test_upsert_user_does_not_reset_language(self) -> None:
        self.db.set_language(7, "uz")
        self.db.upsert_user(7, "ali", "Ali")
        self.assertEqual(self.db.get_language(7), "uz")
        user = self.db.get_user(7)
        self.assertEqual(user["username"], "ali")
        self.assertEqual(self.db.count_users(), 1)

    def test_add_and_get_movie(self) -> None:
        movie = self._add(
            code=10,
            title="Inception",
            description="dream",
            year=2010,
            genre="sci-fi",
            created_by=1,
        )
        self.assertEqual(movie.code, 10)
        self.assertEqual(movie.title, "Inception")
        self.assertEqual(movie.year, 2010)
        got = self.db.get_movie_by_code(10)
        self.assertIsNotNone(got)
        self.assertEqual(got.title, "Inception")
        self.assertTrue(self.db.code_exists(10))
        self.assertFalse(self.db.code_exists(11))

    def test_add_movie_requires_title_and_positive_code(self) -> None:
        with self.assertRaises(ValueError):
            self._add(code=1, title="  ")
        with self.assertRaises(ValueError):
            self._add(code=0, title="X")
        with self.assertRaises(ValueError):
            self._add(code=-3, title="X")

    def test_duplicate_code_rejected(self) -> None:
        self._add(code=1, title="A")
        with self.assertRaises(ValueError):
            self._add(code=1, title="B")

    def test_next_free_code_reuses_gaps(self) -> None:
        self.assertEqual(self.db.next_free_code(), 1)
        self._add(code=1, title="A")
        self._add(code=2, title="B")
        self._add(code=4, title="D")
        self.assertEqual(self.db.next_free_code(), 3)
        self.db.delete_movie(2)
        self.assertEqual(self.db.next_free_code(), 2)
        self._add(code=2, title="B2")
        self._add(code=3, title="C")
        self.assertEqual(self.db.next_free_code(), 5)

    def test_delete_movie(self) -> None:
        self._add(code=8, title="Gone")
        self.assertTrue(self.db.delete_movie(8))
        self.assertFalse(self.db.delete_movie(8))
        self.assertIsNone(self.db.get_movie_by_code(8))

    def test_update_movie_fields(self) -> None:
        self._add(code=3, title="Old", year=2000, genre="a")
        updated = self.db.update_movie(
            3, title="New", year=None, genre="drama", description="ok"
        )
        self.assertEqual(updated.title, "New")
        self.assertIsNone(updated.year)
        self.assertEqual(updated.genre, "drama")
        self.assertEqual(updated.description, "ok")

    def test_update_movie_code_and_conflict(self) -> None:
        self._add(code=1, title="A")
        self._add(code=2, title="B")
        with self.assertRaises(ValueError):
            self.db.update_movie(1, code=2)
        moved = self.db.update_movie(2, code=5)
        self.assertEqual(moved.code, 5)
        self.assertIsNone(self.db.get_movie_by_code(2))
        self.assertEqual(self.db.get_movie_by_code(5).title, "B")

    def test_views_and_top(self) -> None:
        self._add(code=1, title="Low")
        self._add(code=2, title="High")
        self._add(code=3, title="Mid")
        self.assertEqual(self.db.increment_views(2), 1)
        self.assertEqual(self.db.increment_views(2), 2)
        self.db.increment_views(3)
        top = self.db.top_movies(2)
        self.assertEqual([m.title for m in top], ["High", "Mid"])
        self.assertEqual(top[0].views, 2)

    def test_list_movies_pagination(self) -> None:
        for i in range(1, 6):
            self._add(code=i, title=f"F{i}", file_id=f"id{i}")
        page, total = self.db.list_movies(offset=2, limit=2)
        self.assertEqual(total, 5)
        self.assertEqual([m.code for m in page], [3, 4])

    def test_searches_and_stats(self) -> None:
        self.db.upsert_user(10, "u", "U")
        self._add(code=1, title="A")
        self.db.log_search(10, 1, True)
        self.db.log_search(10, 99, False)
        self.db.increment_views(1)
        stats = self.db.stats()
        self.assertEqual(stats["users"], 1)
        self.assertEqual(stats["movies"], 1)
        self.assertEqual(stats["searches"], 2)
        self.assertEqual(stats["found"], 1)
        self.assertEqual(stats["total_views"], 1)
        self.assertEqual(self.db.all_user_ids(), [10])

    def test_channels_and_subscription_flag(self) -> None:
        self.assertTrue(self.db.subscription_enabled())
        self.assertFalse(self.db.subscription_required())
        ch = self.db.add_channel("@demo", title="Demo", url="https://t.me/demo")
        self.assertEqual(ch.chat_id, "@demo")
        self.assertTrue(self.db.subscription_required())
        with self.assertRaises(ValueError):
            self.db.add_channel("@demo")
        self.assertEqual(len(self.db.list_channels()), 1)
        self.db.set_subscription_enabled(False)
        self.assertFalse(self.db.subscription_required())
        self.assertTrue(self.db.remove_channel(ch.id))
        self.db.set_subscription_enabled(True)
        self.assertFalse(self.db.subscription_required())

    def test_settings(self) -> None:
        self.assertIsNone(self.db.get_setting("missing"))
        self.assertEqual(self.db.get_setting("missing", "x"), "x")
        self.db.set_setting("k", "v1")
        self.db.set_setting("k", "v2")
        self.assertEqual(self.db.get_setting("k"), "v2")



class AdminDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "test.db")

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_add_list_remove_admin(self) -> None:
        self.db.upsert_user(100, "ali", "Ali")
        info = self.db.add_admin(100, added_by=1, username="ali")
        self.assertEqual(info.user_id, 100)
        self.assertEqual(info.username, "ali")
        self.assertEqual(info.first_name, "Ali")
        self.assertFalse(info.is_owner)
        self.assertTrue(self.db.is_db_admin(100))
        self.assertFalse(self.db.is_db_admin(999))
        listed = self.db.list_admins(owner_ids=())
        self.assertEqual([a.user_id for a in listed], [100])
        self.assertTrue(self.db.remove_db_admin(100))
        self.assertFalse(self.db.is_db_admin(100))
        self.assertFalse(self.db.remove_db_admin(100))

    def test_duplicate_admin_rejected(self) -> None:
        self.db.add_admin(5, added_by=1)
        with self.assertRaises(ValueError):
            self.db.add_admin(5, added_by=1)
        with self.assertRaises(ValueError):
            self.db.add_admin(0)

    def test_list_admins_merges_owners_without_duplicates(self) -> None:
        self.db.upsert_user(1, "owner", "Owner")
        self.db.upsert_user(2, "mod", "Mod")
        self.db.add_admin(2, added_by=1, username="mod")
        # владельца ошибочно добавили в таблицу — в списке он один раз и как главный
        self.db.add_admin(1, added_by=1, username="owner")
        listed = self.db.list_admins(owner_ids={1, 9})
        ids = [a.user_id for a in listed]
        self.assertEqual(ids, [1, 9, 2])  # owners first (by id), then extras
        by_id = {a.user_id: a for a in listed}
        self.assertTrue(by_id[1].is_owner)
        self.assertTrue(by_id[9].is_owner)
        self.assertFalse(by_id[2].is_owner)
        self.assertEqual(by_id[1].first_name, "Owner")
        self.assertIsNone(by_id[9].first_name)  # нет в users

    def test_find_user_by_username(self) -> None:
        self.db.upsert_user(42, "Cool_User", "C")
        row = self.db.find_user_by_username("@cool_user")
        self.assertIsNotNone(row)
        self.assertEqual(row["user_id"], 42)
        self.assertIsNone(self.db.find_user_by_username("nobody"))
        self.assertIsNone(self.db.find_user_by_username(""))

    def test_migration_keeps_existing_movies(self) -> None:
        movie = self.db.add_movie(code=7, title="Kept")
        path = self.db.path
        self.db.close()
        import sqlite3

        conn = sqlite3.connect(path)
        conn.execute("DROP TABLE admins")
        conn.commit()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("admins", tables)
        conn.close()

        db2 = Database(path)
        self.addCleanup(db2.close)
        tables = {
            r["name"] if hasattr(r, "keys") else r[0]
            for r in db2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        # Row supports index
        names = {row[0] for row in db2.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("admins", names)
        kept = db2.get_movie_by_code(7)
        self.assertIsNotNone(kept)
        self.assertEqual(kept.title, "Kept")
        db2.add_admin(3, added_by=1)
        self.assertTrue(db2.is_db_admin(3))



class MovieSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_add_movie_without_poster(self) -> None:
        db = Database(self.path)
        self.addCleanup(db.close)
        movie = db.add_movie(code=1, title="Dune", year=2021, genre="sci-fi")
        self.assertIsNone(movie.poster_file_id)
        self.assertEqual(movie.title, "Dune")
        got = db.get_movie_by_code(1)
        self.assertIsNotNone(got)
        self.assertIsNone(got.poster_file_id)

    def test_add_and_update_poster(self) -> None:
        db = Database(self.path)
        self.addCleanup(db.close)
        db.add_movie(code=1, title="Dune", poster_file_id="photo_aaa")
        self.assertEqual(db.get_movie_by_code(1).poster_file_id, "photo_aaa")
        db.update_movie(1, poster_file_id="photo_bbb")
        self.assertEqual(db.get_movie_by_code(1).poster_file_id, "photo_bbb")
        db.update_movie(1, poster_file_id=None)
        self.assertIsNone(db.get_movie_by_code(1).poster_file_id)

    def test_migrate_old_file_id_schema_keeps_data(self) -> None:
        import sqlite3
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn = sqlite3.connect(self.path)
        conn.executescript(
            """
            CREATE TABLE movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                year INTEGER,
                genre TEXT,
                file_id TEXT NOT NULL,
                file_unique_id TEXT,
                views INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by INTEGER
            );
            CREATE TABLE channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL UNIQUE,
                title TEXT,
                url TEXT,
                added_at TEXT NOT NULL
            );
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO movies(code, title, description, year, genre, file_id, views, created_at) "
            "VALUES(7, 'Old Film', 'desc', 1999, 'drama', 'video_xxx', 5, ?)",
            (now,),
        )
        conn.execute(
            "INSERT INTO channels(chat_id, title, url, added_at) VALUES('@demo', 'Demo', 'https://t.me/demo', ?)",
            (now,),
        )
        conn.execute("INSERT INTO settings(key, value) VALUES('subscription_enabled', '1')")
        conn.commit()
        conn.close()

        db = Database(self.path)
        self.addCleanup(db.close)
        cols = {row[1] for row in db.execute("PRAGMA table_info(movies)").fetchall()}
        self.assertIn("poster_file_id", cols)
        self.assertNotIn("file_id", cols)
        movie = db.get_movie_by_code(7)
        self.assertIsNotNone(movie)
        self.assertEqual(movie.title, "Old Film")
        self.assertEqual(movie.year, 1999)
        self.assertEqual(movie.views, 5)
        self.assertIsNone(movie.poster_file_id)  # старое видео не считаем постером
        channels = db.list_channels()
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0].chat_id, "@demo")
        self.assertEqual(db.get_setting("subscription_enabled"), "1")
        added = db.add_movie(code=8, title="New Film")
        self.assertIsNone(added.poster_file_id)


if __name__ == "__main__":
    unittest.main()
