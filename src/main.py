"""Entrypoint. Transport switch based on env.

stdio (default, engineer mode): `python src/main.py`
http (platform mode): `MCP_TRANSPORT=http MCP_PORT=8080 python src/main.py`

Lifespan:
    The FastMCP server is wired with a lifespan that builds a long-lived
    Fetcher once at startup and yields it inside an AppContext. Tools access
    the fetcher via `ctx.request_context.lifespan_context.fetcher`. Replace
    `SERVICE_BASE_URL` / `SERVICE_API_KEY` with whatever your upstream API
    expects; rename to `<SERVICE>_BASE_URL` / `<SERVICE>_API_KEY` if your
    service prefix differs from the literal `service` placeholder.
"""
from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass

import uvicorn
from fastmcp import FastMCP
from pythonjsonlogger.json import JsonFormatter

from fetcher import Fetcher
from health import attach_health_endpoints, set_ready
from module_util import discover_modules


def _configure_logging() -> None:
    fmt = os.getenv("LOG_FORMAT", "text")
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stderr)
    if fmt == "json":
        handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)


@dataclass
class AppContext:
    """Lifespan-scoped state exposed to tools.

    Tools access this via `ctx.request_context.lifespan_context.<field>`. Add
    fields here when a tool needs a long-lived resource (DB pool, secondary
    HTTP client, cached config). Anything mutable must be safe for concurrent
    tool calls.
    """
    fetcher: Fetcher


def _build_lifespan() -> Callable[[FastMCP], AbstractAsyncContextManager[AppContext]]:
    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
        base_url = os.environ.get("SERVICE_BASE_URL", "https://api.example.com")
        headers: dict[str, str] = {}
        api_key = os.environ.get("SERVICE_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        fetcher = Fetcher(base_url=base_url, headers=headers)
        try:
            yield AppContext(fetcher=fetcher)
        finally:
            await fetcher.aclose()
    return lifespan


def build_server(*, server_name: str) -> FastMCP:
    _configure_logging()
    mcp = FastMCP(server_name, lifespan=_build_lifespan())
    discover_modules(mcp, components_path=os.path.join(os.path.dirname(__file__), "custom_components"))
    return mcp


def run(server: FastMCP, *, transport: str, port: int, host: str = "0.0.0.0") -> None:
    if transport == "http":
        # stateless_http=True is supported on http_app() (not on FastMCP.__init__).
        # Build the ASGI app here so we can attach health routes to the same object
        # that uvicorn will serve. server.run() would call http_app() again internally,
        # creating a separate instance where our routes would be lost.
        app = server.http_app(stateless_http=True)
        attach_health_endpoints(app)
        set_ready()
        uvicorn.run(app, host=host, port=port)
    else:
        server.run()


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    port = int(os.getenv("MCP_PORT", "8080"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    server_name = os.getenv("MCP_SERVER_NAME", "service_mcp")
    server = build_server(server_name=server_name)
    run(server, transport=transport, port=port, host=host)
