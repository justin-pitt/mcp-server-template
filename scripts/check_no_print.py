"""Verify no print() calls in src/ (stdio MCPs must not corrupt JSON-RPC channel)."""
from __future__ import annotations
import ast
import sys
from pathlib import Path


_EXCLUDED_DIRS = {"test", "tests", "fixtures"}


def main(paths: list[str]) -> int:
    failures = 0
    for path_str in paths:
        for py in Path(path_str).rglob("*.py"):
            if _EXCLUDED_DIRS.intersection(py.parts):
                continue
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                    sys.stdout.write(f"{py}:{node.lineno}: print() call in production code\n")
                    failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["src"]))
