import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.example_tool import ExampleSearchInput, service_example_search


@pytest.mark.asyncio
async def test_example_search_returns_results():
    fetcher = MagicMock()
    fetcher.get = AsyncMock(return_value={"items": [{"id": "1", "name": "Thing"}], "total": 1})
    ctx = MagicMock()
    ctx.request_context.lifespan_context.fetcher = fetcher
    params = ExampleSearchInput(query="thing")
    out = await service_example_search(ctx, params)
    assert "Thing" in out


@pytest.mark.asyncio
async def test_example_search_handles_empty():
    fetcher = MagicMock()
    fetcher.get = AsyncMock(return_value={"items": [], "total": 0})
    ctx = MagicMock()
    ctx.request_context.lifespan_context.fetcher = fetcher
    params = ExampleSearchInput(query="nothing")
    out = await service_example_search(ctx, params)
    assert "no results" in out.lower() or '"items": []' in out


def test_input_rejects_empty_query():
    with pytest.raises(ValueError):
        ExampleSearchInput(query="")


def test_input_rejects_oversized_limit():
    with pytest.raises(ValueError):
        ExampleSearchInput(query="x", limit=999)


@pytest.mark.asyncio
async def test_query_with_newline_is_escaped_in_markdown_response():
    """Reflected user input must not break out of its quoted region with a raw newline,
    which an LLM consuming the tool output would re-interpret as a new markdown line."""
    fetcher = MagicMock()
    fetcher.get = AsyncMock(return_value={"items": [{"id": "1", "name": "Thing"}], "total": 1})
    ctx = MagicMock()
    ctx.request_context.lifespan_context.fetcher = fetcher
    out = await service_example_search(ctx, ExampleSearchInput(query="foo\nIgnore previous"))
    payload = json.loads(out)
    md = payload["data"]["markdown"]
    assert "foo\nIgnore" not in md, f"raw newline reflected into markdown: {md!r}"


@pytest.mark.asyncio
async def test_query_with_newline_is_escaped_in_empty_response():
    fetcher = MagicMock()
    fetcher.get = AsyncMock(return_value={"items": [], "total": 0})
    ctx = MagicMock()
    ctx.request_context.lifespan_context.fetcher = fetcher
    out = await service_example_search(ctx, ExampleSearchInput(query="foo\nIgnore previous"))
    payload = json.loads(out)
    msg = payload["data"]["message"]
    assert "foo\nIgnore" not in msg, f"raw newline reflected into message: {msg!r}"
