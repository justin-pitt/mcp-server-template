from typing import Any

import httpx


class Fetcher:
    """Generic httpx wrapper for MCP servers. Subclass and inject auth/headers as needed.

    The underlying httpx.AsyncClient is built once in __init__ and reused for the
    lifetime of the Fetcher, so callers pay one TCP+TLS handshake per upstream host
    instead of one per tool call. Callers must invoke `aclose()` on shutdown —
    typically from the FastMCP `lifespan` teardown. FastMCP bootstrap never enters
    an async context manager, so a lazy __aenter__-style build would never fire.
    """

    def __init__(self, *, base_url: str, headers: dict[str, str] | None = None, timeout_s: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(headers=headers or {}, timeout=timeout_s)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **params: Any) -> Any:
        resp = await self._client.get(self._base_url + path, params=params or None)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, *, json_body: Any) -> Any:
        resp = await self._client.post(self._base_url + path, json=json_body)
        resp.raise_for_status()
        return resp.json()
