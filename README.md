# mcp-server-template

A production-leaning Python template for building [Model Context Protocol](https://modelcontextprotocol.io) servers with FastMCP. Comes with the scaffolding, tool conventions, and pre-push gates wired up so a new server is a `gh repo create --template` away.

## What's in the box

- **FastMCP-based server** with stdio (engineer mode) and HTTP (platform mode) transports
- **Pluggable tool modules** under `src/custom_components/` discovered at startup
- **Pydantic-typed tool inputs** with `Field(...)` constraints (enforced by `scripts/check_pydantic_inputs.py`)
- **Required tool annotations** (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- **Write-tool gating** via env var so destructive tools can be hidden in read-only environments
- **`/health` and `/metrics`** endpoints in HTTP mode
- **Pre-push gate** running ruff, mypy, pytest, plus three contract checks (Pydantic-inputs, no-bare-print, JWT-library allowlist)
- **Dependabot config** for pip + docker, weekly cadence
- **Multi-stage Dockerfile** with a non-root user, slim Python base, build-arg-controlled Python version

## Scaffold a new server

```bash
gh repo create your-org/<service>-mcp --template justin-pitt/mcp-server-template --private
git clone https://github.com/your-org/<service>-mcp
cd <service>-mcp
```

Replace `{{SERVICE}}` placeholders globally. PowerShell:

```powershell
$service = "myservice"
$files = Get-ChildItem -Recurse -File | Where-Object { -not ($_.FullName -like '*\.git\*') }
foreach ($f in $files) {
  (Get-Content $f.FullName -Raw) -replace '\{\{SERVICE\}\}', $service | Set-Content $f.FullName -NoNewline
}
```

Or POSIX:

```bash
find . -type f -not -path './.git/*' -exec sed -i "s/{{SERVICE}}/myservice/g" {} +
```

Then:

1. Rename `service_mcp` to `<service>_mcp` (underscores) in `pyproject.toml`.
2. Implement tools in `src/custom_components/`. Replace `example_tool.py` with real tools following the same `BaseModule` pattern.
3. `poetry install`, `git config core.hooksPath .githooks`.

## Engineer mode (stdio)

Run as a subprocess from your MCP client's config (e.g. VS Code `.mcp.json` or Claude Desktop):

```json
{
  "mcpServers": {
    "<service>": {
      "command": "C:/path/to/<service>-mcp/venv/Scripts/python.exe",
      "args": ["C:/path/to/<service>-mcp/src/main.py"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "<SERVICE>_API_KEY": "..."
      }
    }
  }
}
```

## Platform mode (HTTP)

The Dockerfile builds an image that listens on `:8080`. Set `MCP_TRANSPORT=http`, point at your auth layer (the server reads `X-Forwarded-User`; it does not validate JWTs itself). `LOG_FORMAT=json` for structured logs.

## Development

```bash
poetry install
git config core.hooksPath .githooks   # one-time: wire the pre-push contract gate

poetry run pytest -v
poetry run ruff check src tests
poetry run mypy src
poetry run python src/main.py                          # stdio
MCP_TRANSPORT=http poetry run python src/main.py       # http (smoke test only)
```

The pre-push hook runs ruff, mypy, the three contract checks, and pytest before allowing a push. To skip it once (e.g. WIP push to a feature branch), use `git push --no-verify` — but the gate exists for good reason; fix the underlying issue rather than habitually skipping it.

## Tool authoring conventions

Each tool MUST:

1. Live in a file under `src/custom_components/` whose top-level class subclasses `BaseModule` and registers tools in `register_tools()` via `self._add_tool(fn, annotations=...)`.
2. Be named `<service>_*` (the prefix matches the FastMCP server name and gates discovery).
3. Take exactly one non-context arg, annotated as a Pydantic `BaseModel` subclass with `ConfigDict(extra="forbid")` and `Field(...)` constraints.
4. Set all four annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`.
5. Have a docstring including description, args, returns, examples, and error handling.

If your server has destructive tools (anything that creates/updates/deletes external state), gate them behind a `<SERVICE>_WRITE_TOOLS_ENABLED` env var. The pattern: register read tools unconditionally, wrap write-tool registration in `if is_write_tools_enabled():`. Unregistered tools are invisible to the client, not just refused at call time.

## License

MIT. See [LICENSE](LICENSE).
