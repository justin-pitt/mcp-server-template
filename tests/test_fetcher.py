import httpx
import pytest
import respx

from fetcher import Fetcher


@pytest.mark.asyncio
@respx.mock
async def test_fetcher_get_returns_json():
    respx.get("https://api.example.com/things/1").mock(return_value=httpx.Response(200, json={"id": "1"}))
    f = Fetcher(base_url="https://api.example.com")
    try:
        data = await f.get("/things/1")
    finally:
        await f.aclose()
    assert data == {"id": "1"}


@pytest.mark.asyncio
@respx.mock
async def test_fetcher_raises_on_4xx():
    respx.get("https://api.example.com/things/missing").mock(return_value=httpx.Response(404, json={"error": "nope"}))
    f = Fetcher(base_url="https://api.example.com")
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await f.get("/things/missing")
    finally:
        await f.aclose()


@pytest.mark.asyncio
async def test_fetcher_reuses_client_across_calls():
    """The client is built once in __init__ and reused across get/post calls,
    so tools don't pay a fresh TCP+TLS handshake per invocation. Verified by
    asserting the underlying AsyncClient instance is stable."""
    f = Fetcher(base_url="https://api.example.com")
    try:
        first = f._client
        # After multiple operations, same client instance still attached.
        with respx.mock:
            respx.get("https://api.example.com/a").mock(return_value=httpx.Response(200, json={}))
            respx.get("https://api.example.com/b").mock(return_value=httpx.Response(200, json={}))
            await f.get("/a")
            await f.get("/b")
        assert f._client is first
    finally:
        await f.aclose()


@pytest.mark.asyncio
async def test_fetcher_aclose_closes_client():
    """aclose() releases the underlying httpx client. Subsequent calls error."""
    f = Fetcher(base_url="https://api.example.com")
    assert not f._client.is_closed
    await f.aclose()
    assert f._client.is_closed
