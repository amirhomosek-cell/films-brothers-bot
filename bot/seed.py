"""Посев фильмов из committed JSON. Существующие коды не перезаписываются."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bot.config import ROOT_DIR

DEFAULT_MOVIES_SEED_PATH = ROOT_DIR / "data_seed" / "movies.json"


@dataclass(frozen=True)
class SeedMovie:
    code: int
    title: str
    description: str | None = None
    year: int | None = None
    genre: str | None = None
    poster_file_id: str | None = None


def load_movies_seed(path: Path) -> tuple[SeedMovie, ...]:
    """Читает массив фильмов. Пустой или отсутствующий файл даёт пустой список."""
    if not path.is_file():
        return ()
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return ()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Некорректный JSON в {path}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"Сиды фильмов в {path} должны быть JSON-массивом.")
    movies: list[SeedMovie] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Элемент {i} в {path} должен быть объектом.")
        try:
            code = int(item["code"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Элемент {i} в {path}: нужен целочисленный code.") from exc
        title = str(item.get("title") or "").strip()
        if code < 1 or not title:
            raise ValueError(
                f"Элемент {i} в {path}: нужны code >= 1 и непустое title."
            )
        year_raw = item.get("year")
        year = int(year_raw) if year_raw not in (None, "") else None
        desc = item.get("description")
        genre = item.get("genre")
        poster = item.get("poster_file_id")
        movies.append(
            SeedMovie(
                code=code,
                title=title,
                description=(str(desc).strip() if desc else None) or None,
                year=year,
                genre=(str(genre).strip() if genre else None) or None,
                poster_file_id=(str(poster).strip() if poster else None) or None,
            )
        )
    return tuple(movies)
