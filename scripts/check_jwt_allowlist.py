"""Verify no JWT/auth libraries are declared or installed unless allowlisted in pyproject.toml.

Checks both the declared deps in pyproject.toml (catches additions made before
`poetry install` is rerun) and the currently-installed packages (catches transitive
pulls from upstream releases). Either path that surfaces a forbidden lib fails the gate.
"""
from __future__ import annotations
import sys
import tomllib
from importlib.metadata import distributions
from typing import Any

JWT_LIBS = {"python-jose", "pyjwt", "authlib"}


def _declared_deps(pyproject: dict[str, Any]) -> set[str]:
    """Names declared under [tool.poetry.dependencies] and any [tool.poetry.group.*.dependencies]."""
    names: set[str] = set()
    poetry_section = pyproject.get("tool", {}).get("poetry", {})
    for dep_name in poetry_section.get("dependencies", {}):
        if dep_name.lower() != "python":
            names.add(dep_name.lower())
    for group in poetry_section.get("group", {}).values():
        for dep_name in group.get("dependencies", {}):
            names.add(dep_name.lower())
    return names


def _installed_deps() -> set[str]:
    return {d.metadata["Name"].lower() for d in distributions()}


def main(pyproject_path: str = "pyproject.toml") -> int:
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    allowlist = {a.lower() for a in pyproject.get("tool", {}).get("mcp-template", {}).get("jwt-allowlist", [])}
    candidates = _declared_deps(pyproject) | _installed_deps()
    forbidden = (JWT_LIBS & candidates) - allowlist
    if forbidden:
        sys.stdout.write(f"ERROR: forbidden JWT libraries present: {sorted(forbidden)}\n")
        sys.stdout.write("Add to pyproject.toml [tool.mcp-template] jwt-allowlist if intentional.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
