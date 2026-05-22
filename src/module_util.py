import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any

from base_module import BaseModule


def discover_modules(mcp: Any, *, components_path: str = "src/custom_components") -> list[BaseModule]:
    """Walk components_path, import every .py file, instantiate every BaseModule subclass."""
    instances: list[BaseModule] = []
    components_dir = Path(components_path).resolve()
    package_name = components_dir.name
    for py in sorted(components_dir.glob("*.py")):
        if py.name == "__init__.py":
            continue
        # Use a fully-qualified unique name to avoid collisions with same-named
        # packages elsewhere on sys.path (e.g. during tests with tmp_path fixtures).
        module_name = f"{components_dir}::{package_name}.{py.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls is BaseModule:
                continue
            if issubclass(cls, BaseModule) and cls.__module__ == module_name:
                instances.append(cls(mcp))
    for inst in instances:
        inst.register_tools()
        inst.register_resources()
    return instances
