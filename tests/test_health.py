"""Тесты HTTP-сервера / и /health."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.health import create_health_app


class HealthAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = TestClient(TestServer(create_health_app()))
        await self.client.start_server()

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_root_and_health_ok(self) -> None:
        for path in ("/", "/health"):
            resp = await self.client.get(path)
            self.assertEqual(resp.status, 200)
            self.assertEqual(await resp.text(), "ok")
