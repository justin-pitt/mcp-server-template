## Summary

<!-- 1-3 bullets on what changed and why -->

## Contract checklist

- [ ] All tools have Pydantic input models with `Field(...)` constraints
- [ ] All tools have all four annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`)
- [ ] All tool names start with `<service>_` prefix
- [ ] List-returning tools accept `limit`/`offset`, return `has_more`/`next_offset`/`total_count`
- [ ] List/get tools accept `response_format=markdown|json`
- [ ] Tool docstrings include description, args, returns, examples, error handling
- [ ] No new JWT/auth libraries added (or, if added, listed in `pyproject.toml [tool.mcp-template] jwt-allowlist` with rationale)
- [ ] Pre-push hook passes locally

## Test plan

<!-- Bulleted list of how to verify -->
