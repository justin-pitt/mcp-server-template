"""Tests for the source-level Pydantic-input gate."""
from __future__ import annotations

import ast

import check_pydantic_inputs as cpi


def scan(source: str) -> list[str]:
    tree = ast.parse(source)
    classes = cpi.collect_pydantic_classes(tree)
    return cpi.find_violations(tree, classes)


def test_bare_basemodel_subclass_passes():
    """Existing pattern: `class Foo(BaseModel)` directly."""
    src = """
from pydantic import BaseModel

class Foo(BaseModel):
    pass

@mcp.tool
async def x_search(ctx, params: Foo):
    pass
"""
    assert scan(src) == []


def test_attribute_base_class_passes():
    """Pattern: `class Foo(pydantic.BaseModel)`. Currently rejected by the narrow check."""
    src = """
import pydantic

class Foo(pydantic.BaseModel):
    pass

@mcp.tool
async def x_search(ctx, params: Foo):
    pass
"""
    assert scan(src) == []


def test_aliased_basemodel_subclass_passes():
    """Pattern: `from pydantic import BaseModel as BM; class Foo(BM)`."""
    src = """
from pydantic import BaseModel as BM

class Foo(BM):
    pass

@mcp.tool
async def x_search(ctx, params: Foo):
    pass
"""
    assert scan(src) == []


def test_transitive_subclass_passes():
    """Pattern: subclass-of-subclass chain rooted on BaseModel."""
    src = """
from pydantic import BaseModel

class Parent(BaseModel):
    pass

class Child(Parent):
    pass

@mcp.tool
async def x_search(ctx, params: Child):
    pass
"""
    assert scan(src) == []


def test_async_tool_with_non_pydantic_arg_fails():
    """Existing behavior: bare-typed async tool arg flagged."""
    src = """
@mcp.tool
async def x_search(ctx, query: str):
    pass
"""
    assert scan(src), "expected a violation for bare-typed arg"


def test_sync_tool_with_non_pydantic_arg_fails():
    """Sync `def` tools must also be checked. Currently silently skipped."""
    src = """
@mcp.tool
def x_search(ctx, query: str):
    pass
"""
    assert scan(src), "expected a violation for bare-typed sync tool"


def test_sync_tool_with_pydantic_arg_passes():
    src = """
from pydantic import BaseModel

class Foo(BaseModel):
    pass

@mcp.tool
def x_search(ctx, params: Foo):
    pass
"""
    assert scan(src) == []


def test_tool_with_too_many_args_fails():
    src = """
from pydantic import BaseModel

class Foo(BaseModel):
    pass

@mcp.tool
async def x_search(ctx, params: Foo, extra: str):
    pass
"""
    assert scan(src), "expected a violation for too many args"


def test_add_tool_indirection_with_pydantic_passes():
    """The template's actual registration pattern: BaseModule._add_tool(fn, ...).
    The gate must follow the indirection and validate the referenced function."""
    src = """
from pydantic import BaseModel
from base_module import BaseModule

class Foo(BaseModel):
    pass

async def x_search(ctx, params: Foo):
    pass

class M(BaseModule):
    def register_tools(self):
        self._add_tool(x_search, annotations={})
    def register_resources(self):
        pass
"""
    assert scan(src) == []


def test_add_tool_indirection_with_non_pydantic_fails():
    """Same registration pattern, but the registered function has a bare-typed arg.
    The current gate (which only looks at @decorator forms) misses this entirely."""
    src = """
from base_module import BaseModule

async def x_search(ctx, query: str):
    pass

class M(BaseModule):
    def register_tools(self):
        self._add_tool(x_search, annotations={})
    def register_resources(self):
        pass
"""
    assert scan(src), "expected a violation: _add_tool(x_search,...) registers a tool with non-Pydantic input"


def test_add_tool_indirection_with_unknown_function_ignored():
    """If _add_tool references a name we can't resolve to a def in the same module
    (e.g. imported from elsewhere), the gate should skip silently rather than crash."""
    src = """
from base_module import BaseModule
from somewhere import imported_tool

class M(BaseModule):
    def register_tools(self):
        self._add_tool(imported_tool, annotations={})
    def register_resources(self):
        pass
"""
    assert scan(src) == []


def test_add_tool_indirection_with_missing_pydantic_input_fails():
    """_add_tool(fn) where fn has no params annotation at all."""
    src = """
from base_module import BaseModule

async def x_search(ctx, query):
    pass

class M(BaseModule):
    def register_tools(self):
        self._add_tool(x_search, annotations={})
    def register_resources(self):
        pass
"""
    assert scan(src), "expected a violation: untyped arg on _add_tool-registered function"
