"""Health and metrics endpoints. Attached to FastMCP's Starlette ASGI app in HTTP mode."""
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

_ready = False
tool_calls = Counter("mcp_tool_calls_total", "Tool calls", ["tool", "outcome"])
tool_latency = Histogram("mcp_tool_call_duration_seconds", "Tool call latency", ["tool"])


def set_ready() -> None:
    global _ready
    _ready = True


async def _health(request: Request) -> Response:
    if _ready:
        return Response(status_code=200, content='{"status":"ok"}', media_type="application/json")
    return Response(status_code=503, content='{"status":"not_ready"}', media_type="application/json")


async def _metrics(request: Request) -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def attach_health_endpoints(app: Starlette) -> None:
    """Attach /health and /metrics routes to any Starlette-compatible ASGI app."""
    app.add_route("/health", _health, methods=["GET"])
    app.add_route("/metrics", _metrics, methods=["GET"])


def health_routes() -> list[Route]:
    """Return /health and /metrics as Starlette Route objects for use in composite apps."""
    return [
        Route("/health", _health, methods=["GET"]),
        Route("/metrics", _metrics, methods=["GET"]),
    ]
