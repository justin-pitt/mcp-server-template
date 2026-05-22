# CLAUDE.md

Guidance for Claude (and similar coding agents) working inside an MCP server scaffolded from this template. Defaults here match `scripts/check_pydantic_inputs.py`, `scripts/check_no_print.py`, and `scripts/check_jwt_allowlist.py` enforcement.

## Adding a tool

1. Create `src/custom_components/<area>.py` following the `example_tool.py` pattern. The file defines a `BaseModule` subclass plus tool functions; the discovery loop in `src/module_util.py` instantiates each class at server start.
2. Tool function name MUST start with `<service>_` (matches the FastMCP server name and gates discovery).
3. Tool input MUST be a single Pydantic `BaseModel` subclass with `ConfigDict(extra="forbid")` and `Field(...)` constraints. No bare positional args.
4. Tool MUST set all four annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`.
5. List-returning tools accept `limit: int` + `offset: int` and return `items`, `total_count`, `has_more`, `next_offset` alongside the data.
6. List and get tools accept `response_format: Literal["markdown", "json"] = "markdown"`.
7. Tool docstring includes description, args, returns, examples, and error handling.
8. Add a test in `tests/test_<area>.py` mocking the fetcher or connector singleton (do not instantiate real HTTP clients in unit tests).
9. Run the full pre-push gate: `poetry run pytest -v && poetry run ruff check src tests && poetry run mypy src && poetry run python scripts/check_pydantic_inputs.py src && poetry run python scripts/check_no_print.py src && poetry run python scripts/check_jwt_allowlist.py`.

## Commands

```bash
poetry install
git config core.hooksPath .githooks                    # one-time wire of the gate

poetry run pytest -v
poetry run pytest tests/test_<area>.py::test_<name>    # single test
poetry run ruff check src tests
poetry run mypy src

poetry run python src/main.py                          # stdio (engineer mode)
MCP_TRANSPORT=http poetry run python src/main.py       # http (smoke test only)
```

## Permission tiers

If the server has destructive tools, gate them with `<SERVICE>_WRITE_TOOLS_ENABLED`. Read tools are always registered; write tools are registered only when the env flag is truthy. Unregistered tools are invisible to the client.

```python
def register_tools(self) -> None:
    self._add_tool(get_thing, annotations={"title": "Get Thing", **_READ_ANNOTATIONS})
    if is_write_tools_enabled():
        self._add_tool(create_thing, annotations={"title": "Create Thing", **_WRITE_ANNOTATIONS})
```

## No bare `print()`

stdio MCP servers MUST NOT write to stdout (it's the wire protocol). `scripts/check_no_print.py` blocks bare `print()` in `src/`. Use `logging.getLogger(__name__)` and let it write to stderr.

## JWT-library allowlist

`scripts/check_jwt_allowlist.py` fails the gate if `python-jose`, `pyjwt`, or `authlib` are declared or transitively installed unless explicitly allowlisted under `pyproject.toml [tool.mcp-template] jwt-allowlist` with rationale. The assumption is that an auth layer (gateway, sidecar, ingress filter) handles JWTs; the server reads `X-Forwarded-User` only. Override only with a clear reason.
