"""Необязательный HTTP-сервер для платформ, которым нужен открытый $PORT."""

from __future__ import annotations

import logging

from aiohttp import web

logger = logging.getLogger(__name__)


async def handle_ok(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


def create_health_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_ok)
    app.router.add_get("/health", handle_ok)
    return app


async def start_health_server(port: int, host: str = "0.0.0.0") -> web.AppRunner:
    runner = web.AppRunner(create_health_app())
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("HTTP-сервер проверки: %s:%s (/ и /health)", host, port)
    return runner
