"""Read-only example tool. Copy this pattern when implementing new tools.

Replace 'service' with your service prefix everywhere (also in pyproject.toml's name).
The function name MUST start with `<service>_` to satisfy contract item 14.
"""
from enum import Enum

from fastmcp import Context
from pydantic import BaseModel, ConfigDict, Field, field_validator

from base_module import BaseModule
from pkg.util import create_response


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class ExampleSearchInput(BaseModel):
    """Input model for service_example_search."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(..., description="Search string. Example: 'alerts'.", min_length=1, max_length=200)
    limit: int | None = Field(default=20, description="Max results.", ge=1, le=100)
    offset: int | None = Field(default=0, description="Pagination offset.", ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format.")

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be blank")
        return v


async def service_example_search(ctx: Context, params: ExampleSearchInput) -> str:
    """Search example resources by query string.

    Args:
        ctx: FastMCP context. The lifespan in main.py attaches a Fetcher to
            ctx.request_context.lifespan_context.fetcher.
        params: ExampleSearchInput.

    Returns:
        Markdown or JSON response. Always wrapped via create_response.

    Examples:
        - Use when: "find resources matching X" -> ExampleSearchInput(query="X")
        - Don't use when: you have a specific resource ID (use service_get_resource).

    Error handling:
        - Pydantic validates input; raises ValueError on bad input.
        - HTTP errors propagate from fetcher.get; caller handles.
    """
    # request_context is None outside an MCP request (e.g. unit tests that
    # bypass the framework). Assert non-None to satisfy mypy; FastMCP guarantees
    # it's set whenever a tool is actually invoked.
    assert ctx.request_context is not None
    fetcher = ctx.request_context.lifespan_context.fetcher
    data = await fetcher.get("/things", q=params.query, limit=params.limit, offset=params.offset)
    items = data.get("items", [])
    total = data.get("total", 0)

    if params.response_format == ResponseFormat.JSON:
        return create_response(data={
            "total": total,
            "count": len(items),
            "offset": params.offset,
            "items": items,
            "has_more": total > (params.offset or 0) + len(items),
            "next_offset": (params.offset or 0) + len(items) if total > (params.offset or 0) + len(items) else None,
        })

    # Use repr() so control chars in the user-supplied query are escaped before they
    # reach a downstream LLM that would otherwise re-interpret a raw newline as a
    # new markdown line.
    if not items:
        return create_response(data={"message": f"No results for {params.query!r}"})
    lines = [f"# Results for {params.query!r}", f"Total: {total}", ""]
    for it in items:
        lines.append(f"- {it.get('name', '<unnamed>')} ({it.get('id', '<no-id>')})")
    return create_response(data={"markdown": "\n".join(lines)})


class ExampleModule(BaseModule):
    def register_tools(self) -> None:
        self._add_tool(
            service_example_search,
            annotations={
                "title": "Example Search",
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": True,
            },
        )

    def register_resources(self) -> None:
        pass
