from unittest.mock import MagicMock

from base_module import BaseModule
from module_util import discover_modules


def test_discover_modules_loads_all_basemodule_subclasses(tmp_path, monkeypatch):
    components = tmp_path / "custom_components"
    components.mkdir()
    (components / "__init__.py").write_text("")
    (components / "fake.py").write_text("""
from base_module import BaseModule

class FakeModule(BaseModule):
    def register_tools(self):
        self.registered = True
    def register_resources(self):
        pass
""")
    monkeypatch.syspath_prepend(str(tmp_path))
    fake_mcp = MagicMock()
    modules = discover_modules(fake_mcp, components_path=str(components))
    assert len(modules) == 1
    assert modules[0].__class__.__name__ == "FakeModule"


def test_basemodule_subclass_registers_tools_and_resources():
    fake_mcp = MagicMock()

    class M(BaseModule):
        def register_tools(self) -> None:
            self.tools_registered = True
        def register_resources(self) -> None:
            self.resources_registered = True

    m = M(fake_mcp)
    m.register_tools()
    m.register_resources()
    assert m.tools_registered is True
    assert m.resources_registered is True
