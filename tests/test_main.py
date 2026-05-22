import asyncio
from unittest.mock import MagicMock, patch

import pytest


def test_main_uses_stdio_by_default(monkeypatch):
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    with patch("main.FastMCP") as mock_fastmcp, patch("main.discover_modules"):
        instance = MagicMock()
        mock_fastmcp.return_value = instance
        from main import build_server, run

        server = build_server(server_name="service_mcp")
        run(server, transport="stdio", port=8080)
        instance.run.assert_called_once_with()


def test_main_uses_http_when_env_set(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    with (
        patch("main.FastMCP") as mock_fastmcp,
        patch("main.discover_modules"),
        patch("main.attach_health_endpoints") as mock_health,
        patch("main.uvicorn") as mock_uvicorn,
    ):
        instance = MagicMock()
        mock_fastmcp.return_value = instance
        from main import build_server, run

        server = build_server(server_name="service_mcp")
        run(server, transport="http", port=8080)

        instance.http_app.assert_called_once_with(stateless_http=True)
        mock_health.assert_called_once_with(instance.http_app.return_value)
        mock_uvicorn.run.assert_called_once()
        call_args = mock_uvicorn.run.call_args
        assert call_args.kwargs.get("port") == 8080


def test_run_default_host_is_all_interfaces():
    """Default host stays 0.0.0.0 so existing platform Helm deploys keep working."""
    with (
        patch("main.attach_health_endpoints"),
        patch("main.uvicorn") as mock_uvicorn,
    ):
        from main import run

        instance = MagicMock()
        run(instance, transport="http", port=8080)

        assert mock_uvicorn.run.call_args.kwargs.get("host") == "0.0.0.0"


def test_run_respects_explicit_host():
    """Explicit host kwarg should override the default and reach uvicorn."""
    with (
        patch("main.attach_health_endpoints"),
        patch("main.uvicorn") as mock_uvicorn,
    ):
        from main import run

        instance = MagicMock()
        run(instance, transport="http", port=8080, host="127.0.0.1")

        assert mock_uvicorn.run.call_args.kwargs.get("host") == "127.0.0.1"


# --- Lifespan ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_yields_appcontext_with_fetcher(monkeypatch):
    monkeypatch.setenv("SERVICE_BASE_URL", "https://api.test.example")
    monkeypatch.delenv("SERVICE_API_KEY", raising=False)
    from main import AppContext, _build_lifespan

    lifespan = _build_lifespan()
    async with lifespan(MagicMock()) as ctx:
        assert isinstance(ctx, AppContext)
        assert ctx.fetcher is not None
        assert ctx.fetcher._base_url == "https://api.test.example"


@pytest.mark.asyncio
async def test_lifespan_closes_fetcher_on_teardown(monkeypatch):
    monkeypatch.setenv("SERVICE_BASE_URL", "https://api.test.example")
    monkeypatch.delenv("SERVICE_API_KEY", raising=False)
    from main import _build_lifespan

    lifespan = _build_lifespan()
    async with lifespan(MagicMock()) as ctx:
        f = ctx.fetcher
        assert not f._client.is_closed
    assert f._client.is_closed


@pytest.mark.asyncio
async def test_lifespan_injects_bearer_when_api_key_set(monkeypatch):
    monkeypatch.setenv("SERVICE_BASE_URL", "https://api.test.example")
    monkeypatch.setenv("SERVICE_API_KEY", "secret-token")
    from main import _build_lifespan

    lifespan = _build_lifespan()
    async with lifespan(MagicMock()) as ctx:
        auth = ctx.fetcher._client.headers.get("Authorization")
        assert auth == "Bearer secret-token"


def test_build_server_passes_lifespan_to_fastmcp(monkeypatch):
    monkeypatch.delenv("SERVICE_API_KEY", raising=False)
    with patch("main.FastMCP") as mock_fastmcp, patch("main.discover_modules"):
        from main import build_server

        build_server(server_name="service_mcp")
        kwargs = mock_fastmcp.call_args.kwargs
        assert "lifespan" in kwargs and callable(kwargs["lifespan"])


def test_build_server_registers_tools_regardless_of_cwd(monkeypatch, tmp_path):
    """Regression: build_server must locate custom_components/ independent of process cwd.

    Bug: discover_modules was called with a relative path "src/custom_components"
    which Path.resolve() expands against the current working directory. When the
    MCP harness launched the child process from any cwd other than the project
    root, the glob returned empty and the server started with zero tools and no
    error logged.
    """
    monkeypatch.chdir(tmp_path)
    from main import build_server

    server = build_server(server_name="service_mcp_test")
    tools = asyncio.run(server.list_tools())

    assert len(tools) > 0, (
        f"build_server registered {len(tools)} tools from cwd={tmp_path}; "
        "components_path must not depend on cwd"
    )
