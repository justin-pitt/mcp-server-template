"""Verify every MCP-registered tool function takes a single Pydantic-typed argument (besides ctx).

Catches two registration patterns:
  1. Decorator form: `@mcp.tool` / `@x.tool(...)` / `@tool` on a `def`/`async def`.
  2. Indirection form: `self._add_tool(<fn>, ...)` inside a `BaseModule` subclass's
     `register_tools` method, where `<fn>` resolves to a `def`/`async def` in the
     same module. This is the pattern the fleet template uses, so omitting it
     would let bad inputs pass the gate.

Names referenced by `_add_tool` that don't resolve to a local def (e.g. imported
from another module) are skipped silently; their gate runs in their own file.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

PYDANTIC_BASES = {"BaseModel"}


def collect_pydantic_aliases(tree: ast.Module) -> set[str]:
    """Names that resolve to a pydantic base class in this file: the canonical
    name plus any `from pydantic import BaseModel as X` aliases."""
    aliases: set[str] = set(PYDANTIC_BASES)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "pydantic":
            for alias in node.names:
                if alias.name in PYDANTIC_BASES:
                    aliases.add(alias.asname or alias.name)
    return aliases


def collect_pydantic_classes(tree: ast.Module) -> set[str]:
    """Classes that are Pydantic models. Handles bare-name bases, attribute-access
    bases (e.g. `pydantic.BaseModel`), aliased imports, and transitive subclasses."""
    aliases = collect_pydantic_aliases(tree)
    classes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in aliases:
                    classes.add(node.name)
                elif isinstance(base, ast.Attribute) and base.attr in PYDANTIC_BASES:
                    classes.add(node.name)
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name not in classes:
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in classes:
                        classes.add(node.name)
                        changed = True
    return classes


FuncDef = ast.FunctionDef | ast.AsyncFunctionDef


def _is_tool_decorator(d: ast.expr) -> bool:
    return (
        (isinstance(d, ast.Attribute) and d.attr == "tool")
        or (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "tool")
        or (isinstance(d, ast.Name) and d.id == "tool")
    )


def _collect_top_level_funcs(tree: ast.Module) -> dict[str, FuncDef]:
    """Top-level def/async def in the module, keyed by name. Used to resolve
    function references in `self._add_tool(<name>, ...)` indirection."""
    out: dict[str, FuncDef] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
    return out


def _add_tool_referenced_funcs(tree: ast.Module) -> list[FuncDef]:
    """Functions registered via `self._add_tool(<name>, ...)` inside any class.

    Names that don't resolve to a local def are skipped (their own file's gate
    will catch them; cross-file resolution is out of scope for an AST gate).
    """
    locals_ = _collect_top_level_funcs(tree)
    registered: list[FuncDef] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_add_tool"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
        ):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id in locals_:
            registered.append(locals_[first.id])
    return registered


def _check_func_signature(fn: FuncDef, pydantic_locals: set[str]) -> list[str]:
    """Pydantic-arg invariant on a single tool function."""
    violations: list[str] = []
    non_ctx_args = [a for a in fn.args.args if a.arg != "ctx" and a.arg != "self"]
    if len(non_ctx_args) != 1:
        violations.append(f"{fn.name}: must have exactly one non-ctx arg, has {len(non_ctx_args)}")
        return violations
    arg = non_ctx_args[0]
    if not arg.annotation or not isinstance(arg.annotation, ast.Name) or arg.annotation.id not in pydantic_locals:
        violations.append(f"{fn.name}: arg '{arg.arg}' is not annotated as a Pydantic BaseModel subclass")
    return violations


def find_violations(tree: ast.Module, pydantic_locals: set[str]) -> list[str]:
    violations: list[str] = []
    seen: set[int] = set()
    # Decorator form
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_tool_decorator(d) for d in node.decorator_list):
            continue
        seen.add(id(node))
        violations.extend(_check_func_signature(node, pydantic_locals))
    # _add_tool indirection
    for fn in _add_tool_referenced_funcs(tree):
        if id(fn) in seen:
            continue
        seen.add(id(fn))
        violations.extend(_check_func_signature(fn, pydantic_locals))
    return violations


_EXCLUDED_DIRS = {"test", "tests", "fixtures"}


def main(paths: list[str]) -> int:
    failures = 0
    for path_str in paths:
        for py in Path(path_str).rglob("*.py"):
            if _EXCLUDED_DIRS.intersection(py.parts):
                continue
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
            pydantic_classes = collect_pydantic_classes(tree)
            for v in find_violations(tree, pydantic_classes):
                sys.stdout.write(f"{py}:{v}\n")
                failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["src"]))
