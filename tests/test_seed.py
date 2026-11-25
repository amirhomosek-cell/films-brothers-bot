"""Тесты посева фильмов из JSON. Telegram не нужен."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.db import Database
from bot.seed import DEFAULT_MOVIES_SEED_PATH, SeedMovie, load_movies_seed


class LoadMoviesSeedTests(unittest.TestCase):
    def test_missing_file_is_empty(self) -> None:
        self.assertEqual(load_movies_seed(Path("/no/such/movies.json")), ())

    def test_empty_file_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "movies.json"
            path.write_text("  \n", encoding="utf-8")
            self.assertEqual(load_movies_seed(path), ())

    def test_parses_optional_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "movies.json"
            path.write_text(
                json.dumps(
                    [
                        {
                            "code": 7,
                            "title": "Test",
                            "year": 2001,
                            "genre": "drama",
                            "description": "desc",
                            "poster_file_id": "AgAC-file",
                        },
                        {"code": 8, "title": "Bare"},
                    ]
                ),
                encoding="utf-8",
            )
            movies = load_movies_seed(path)
        self.assertEqual(len(movies), 2)
        self.assertEqual(movies[0].code, 7)
        self.assertEqual(movies[0].poster_file_id, "AgAC-file")
        self.assertEqual(movies[1].code, 8)
        self.assertIsNone(movies[1].year)
        self.assertIsNone(movies[1].poster_file_id)

    def test_invalid_json_and_missing_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "movies.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_movies_seed(path)
            path.write_text('{"code": 1}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_movies_seed(path)
            path.write_text('[{"code": 0, "title": "X"}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_movies_seed(path)
            path.write_text('[{"code": 1, "title": "  "}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_movies_seed(path)

    def test_committed_seed_has_three_known_movies(self) -> None:
        movies = load_movies_seed(DEFAULT_MOVIES_SEED_PATH)
        self.assertEqual(len(movies), 3)
        self.assertEqual([m.code for m in movies], [1, 2, 3])
        self.assertEqual(movies[0].title, "Да здравствует Франция!")
        self.assertEqual(movies[1].title, "Диктатор")
        self.assertEqual(movies[2].title, "Kingsman: секретная служба")
        for movie in movies:
            self.assertTrue(movie.poster_file_id)
            self.assertTrue(movie.year)
            self.assertTrue(movie.genre)
            self.assertTrue(movie.description)


class SeedMoviesDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)  # последним: на Windows открытую базу не удалить
        self.db = Database(Path(self.tmp.name) / "test.db")

    def tearDown(self) -> None:
        self.db.close()

    def test_inserts_only_missing_codes_and_does_not_overwrite(self) -> None:
        self.db.add_movie(code=1, title="OLD TITLE", year=1900, genre="old")
        movies = load_movies_seed(DEFAULT_MOVIES_SEED_PATH)
        added = self.db.seed_movies(movies)
        self.assertEqual(added, 2)
        kept = self.db.get_movie_by_code(1)
        self.assertIsNotNone(kept)
        self.assertEqual(kept.title, "OLD TITLE")
        self.assertEqual(kept.year, 1900)
        self.assertEqual(kept.genre, "old")
        second = self.db.get_movie_by_code(2)
        self.assertEqual(second.title, "Диктатор")
        self.assertEqual(second.year, 2012)
        self.assertTrue(second.poster_file_id)
        third = self.db.get_movie_by_code(3)
        self.assertEqual(third.title, "Kingsman: секретная служба")
        # Повторный посев ничего не меняет и не удаляет.
        added_again = self.db.seed_movies(movies)
        self.assertEqual(added_again, 0)
        self.assertEqual(self.db.get_movie_by_code(1).title, "OLD TITLE")
        items, total = self.db.list_movies(limit=100)
        self.assertEqual(total, 3)
        self.assertEqual(len(items), 3)

    def test_seed_does_not_delete_unrelated_movies(self) -> None:
        self.db.add_movie(code=99, title="Keep me")
        added = self.db.seed_movies(
            [SeedMovie(code=5, title="New", year=2020)]
        )
        self.assertEqual(added, 1)
        self.assertIsNotNone(self.db.get_movie_by_code(99))
        self.assertEqual(self.db.get_movie_by_code(5).title, "New")
