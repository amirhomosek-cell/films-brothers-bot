"""Тесты текстов, подписей и разбора ввода."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.db import Movie
from bot.texts import (
    CAPTION_LIMIT,
    DEFAULT_LANG,
    TEXTS,
    format_caption,
    format_movie_text,
    parse_add_args,
    parse_code,
    parse_extra,
    t,
)
from bot.utils import parse_channel_ref


def _movie(**kwargs) -> Movie:
    data = dict(
        id=1,
        code=12,
        title="Test",
        description=None,
        year=None,
        genre=None,
        poster_file_id=None,
        views=3,
        created_at="now",
        created_by=1,
    )
    data.update(kwargs)
    return Movie(**data)


class TextsTests(unittest.TestCase):
    def test_both_languages_have_same_keys(self) -> None:
        self.assertEqual(set(TEXTS["ru"]), set(TEXTS["uz"]))
        self.assertTrue(TEXTS["ru"])
        self.assertTrue(TEXTS["uz"])

    def test_t_fallback_and_format(self) -> None:
        self.assertIn("не найден", t("ru", "movie_not_found", code=5))
        self.assertIn("topilmadi", t("uz", "movie_not_found", code=5))
        self.assertEqual(t("en", "btn_skip"), TEXTS[DEFAULT_LANG]["btn_skip"])
        self.assertEqual(t("ru", "missing_key_zzz"), "missing_key_zzz")

    def test_format_caption_includes_fields(self) -> None:
        movie = _movie(title="Dune", year=2021, genre="sci-fi", description="sand", views=9)
        cap = format_caption("ru", movie)
        self.assertIn("Dune", cap)
        self.assertIn("12", cap)
        self.assertIn("2021", cap)
        self.assertIn("sci-fi", cap)
        self.assertIn("sand", cap)
        self.assertIn("9", cap)
        self.assertIn("Код", cap)
        uz = format_caption("uz", movie)
        self.assertIn("Kod", uz)

    def test_format_caption_skips_empty_optional_fields(self) -> None:
        cap = format_caption("ru", _movie())
        self.assertNotIn("📅", cap)
        self.assertNotIn("🎭", cap)
        self.assertIn("Test", cap)

    def test_format_caption_truncates_long_description(self) -> None:
        movie = _movie(description="A" * 5000)
        cap = format_caption("ru", movie)
        self.assertLessEqual(len(cap), CAPTION_LIMIT)
        self.assertTrue(cap.endswith("👁 3") or "👁 3" in cap)

    def test_parse_code(self) -> None:
        self.assertEqual(parse_code("12"), 12)
        self.assertEqual(parse_code("  007  "), 7)
        self.assertIsNone(parse_code("0"))
        self.assertIsNone(parse_code("-1"))
        self.assertIsNone(parse_code("12a"))
        self.assertIsNone(parse_code(""))
        self.assertIsNone(parse_code(None))
        self.assertIsNone(parse_code("код 5"))

    def test_parse_extra(self) -> None:
        self.assertEqual(
            parse_extra("2020 | drama | about a hero"),
            {"year": 2020, "genre": "drama", "description": "about a hero"},
        )
        self.assertEqual(
            parse_extra("- | - | -"),
            {"year": None, "genre": None, "description": None},
        )
        self.assertEqual(
            parse_extra("1999"),
            {"year": 1999, "genre": None, "description": None},
        )
        self.assertEqual(
            parse_extra("2024 | боевик | часть 1 | финал"),
            {"year": 2024, "genre": "боевик", "description": "часть 1 | финал"},
        )
        with self.assertRaises(ValueError):
            parse_extra("abcd | x")
        with self.assertRaises(ValueError):
            parse_extra("1500 | x")

    def test_format_movie_text_title_without_views(self) -> None:
        movie = _movie(title="Dune", year=2021, genre="sci-fi", description="sand", views=9)
        text = format_movie_text("ru", movie, include_views=False)
        self.assertIn("<b>Dune</b>", text)
        self.assertIn("2021", text)
        self.assertIn("sci-fi", text)
        self.assertIn("sand", text)
        self.assertNotIn("👁", text)

    def test_parse_add_args(self) -> None:
        self.assertEqual(parse_add_args(None), (None, None))
        self.assertEqual(parse_add_args(""), (None, None))
        self.assertEqual(parse_add_args("12 Интерстеллар"), (12, "Интерстеллар"))
        self.assertEqual(parse_add_args("12"), (12, None))
        self.assertEqual(parse_add_args("Интерстеллар"), (None, "Интерстеллар"))
        self.assertEqual(parse_add_args("007 Dune Part Two"), (7, "Dune Part Two"))

    def test_top_line_hides_title(self) -> None:
        ru = t("ru", "top_line", i=1, code=12, views=340)
        uz = t("uz", "top_line", i=1, code=12, views=340)
        self.assertEqual(ru, "1. Код 12 · 👁 340")
        self.assertEqual(uz, "1. Kod 12 · 👁 340")
        self.assertNotIn("Dune", ru)
        self.assertNotIn("{title}", ru)
        self.assertNotIn("{title}", uz)
        # админский список по-прежнему с названием
        listing = t("ru", "list_line", code=12, title="Dune", views=340)
        self.assertIn("Dune", listing)
        self.assertIn("12", listing)

    def test_parse_channel_ref(self) -> None:

        self.assertEqual(parse_channel_ref("@My_Channel"), "@My_Channel")
        self.assertEqual(parse_channel_ref("https://t.me/mychan"), "@mychan")
        self.assertEqual(parse_channel_ref("-1001234567890"), "-1001234567890")
        self.assertIsNone(parse_channel_ref("https://t.me/+AbCd"))
        self.assertIsNone(parse_channel_ref(""))
        self.assertIsNone(parse_channel_ref("not a channel"))


class ConfigTests(unittest.TestCase):
    def test_parse_admin_ids_and_is_admin(self) -> None:
        from bot.config import Config, _parse_admin_ids

        ids = _parse_admin_ids(" 11, 22;33 , ")
        self.assertEqual(ids, frozenset({11, 22, 33}))
        self.assertEqual(_parse_admin_ids(""), frozenset())
        with self.assertRaises(ValueError):
            _parse_admin_ids("abc")
        cfg = Config(bot_token="", admin_ids=frozenset({11}), db_path=Path("x"))
        self.assertTrue(cfg.is_owner(11))
        self.assertTrue(cfg.is_admin(11))  # в Config — только .env
        self.assertFalse(cfg.is_owner(12))
        self.assertFalse(cfg.is_admin(12))
        self.assertFalse(cfg.is_admin(None))



class AccessTests(unittest.TestCase):
    def test_is_admin_uses_env_and_db(self) -> None:
        import tempfile
        from bot.access import display_name, is_admin, is_owner
        from bot.config import Config
        from bot.db import Database

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database(Path(tmp.name) / "a.db")
        self.addCleanup(db.close)
        cfg = Config(bot_token="", admin_ids=frozenset({11}), db_path=Path("x"))
        self.assertTrue(is_owner(cfg, db, 11))
        self.assertTrue(is_admin(cfg, db, 11))
        self.assertFalse(is_admin(cfg, db, 22))
        db.add_admin(22, added_by=11, username="mod")
        self.assertTrue(is_admin(cfg, db, 22))
        self.assertFalse(is_owner(cfg, db, 22))
        self.assertFalse(is_admin(cfg, db, None))
        db.remove_db_admin(22)
        self.assertFalse(is_admin(cfg, db, 22))

    def test_display_name(self) -> None:
        from bot.access import display_name

        self.assertEqual(display_name(user_id=1, first_name="Ali", username="ali"), "Ali (@ali)")
        self.assertEqual(display_name(user_id=1, first_name="Ali"), "Ali")
        self.assertEqual(display_name(user_id=1, username="ali"), "@ali")
        self.assertEqual(display_name(user_id=7), "ID 7")


if __name__ == "__main__":
    unittest.main()
