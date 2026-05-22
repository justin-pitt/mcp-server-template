from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class BaseModule(ABC):
    """Base class for tool-grouping modules. Subclasses are auto-discovered by module_util."""

    def __init__(self, mcp: Any) -> None:
        self._mcp = mcp

    @abstractmethod
    def register_tools(self) -> None: ...

    @abstractmethod
    def register_resources(self) -> None: ...

    def _add_tool(self, fn: Callable[..., Any], *, annotations: dict[str, Any] | None = None) -> None:
        self._mcp.tool(name=fn.__name__, annotations=annotations or {})(fn)
