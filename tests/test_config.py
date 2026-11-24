"""Тесты разбора настроек. Telegram не нужен."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.config import load_config, parse_required_channels


class ParseRequiredChannelsTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(parse_required_channels(""), ())
        self.assertEqual(parse_required_channels("  , ; "), ())

    def test_chat_id_and_username(self) -> None:
        channels = parse_required_channels("-1003834817665:@musordrop14886752")
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0].chat_id, "-1003834817665")
        self.assertEqual(channels[0].title, "musordrop14886752")
        self.assertEqual(channels[0].url, "https://t.me/musordrop14886752")

    def test_chat_id_only_and_https_and_multiple(self) -> None:
        raw = "-1001, -1002:https://t.me/demo, -1003:@other"
        channels = parse_required_channels(raw)
        self.assertEqual([c.chat_id for c in channels], ["-1001", "-1002", "-1003"])
        self.assertIsNone(channels[0].url)
        self.assertEqual(channels[1].url, "https://t.me/demo")
        self.assertEqual(channels[1].title, "demo")
        self.assertEqual(channels[2].url, "https://t.me/other")

    def test_empty_chat_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_required_channels(":@oops")


class LoadConfigTests(unittest.TestCase):
    def test_port_and_required_channels_from_env(self) -> None:
        env = {
            "BOT_TOKEN": "123:ABC",
            "ADMIN_IDS": "6036662209",
            "PORT": "10000",
            "REQUIRED_CHANNELS": "-1003834817665:@musordrop14886752",
            "DB_PATH": "data/test-unused.db",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            config = load_config(require_token=True)
        self.assertEqual(config.port, 10000)
        self.assertEqual(config.admin_ids, frozenset({6036662209}))
        self.assertEqual(len(config.required_channels), 1)
        self.assertEqual(config.required_channels[0].chat_id, "-1003834817665")

    def test_no_port_means_none(self) -> None:
        env = {
            "BOT_TOKEN": "123:ABC",
            "ADMIN_IDS": "1",
            "PORT": "",
            "REQUIRED_CHANNELS": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ["PORT"] = ""
            os.environ["REQUIRED_CHANNELS"] = ""
            config = load_config(require_token=True)
        self.assertIsNone(config.port)
        self.assertEqual(config.required_channels, ())

    def test_invalid_port(self) -> None:
        env = {"BOT_TOKEN": "123:ABC", "ADMIN_IDS": "1", "PORT": "nope"}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ["PORT"] = "nope"
            with self.assertRaises(ValueError):
                load_config(require_token=True)
