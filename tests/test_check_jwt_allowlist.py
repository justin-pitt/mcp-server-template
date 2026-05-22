"""Tests for the JWT-library allowlist gate."""
from __future__ import annotations

import check_jwt_allowlist as cja
import pytest


@pytest.fixture(autouse=True)
def isolate_installed(monkeypatch):
    """Default: tests see an empty installed-package set so we exercise the
    pyproject-declared path in isolation. Tests that care about the installed
    path override this explicitly."""
    monkeypatch.setattr(cja, "_installed_deps", lambda: set())


def write_pyproject(dir_, body):
    p = dir_ / "pyproject.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_clean_pyproject_passes(tmp_path):
    write_pyproject(tmp_path, """
[tool.poetry]
name = "x"
version = "0.0.1"

[tool.poetry.dependencies]
python = ">=3.12,<4.0"
httpx = "^0.28"
""")
    assert cja.main(str(tmp_path / "pyproject.toml")) == 0


def test_declared_jwt_lib_without_allowlist_fails(tmp_path):
    """Adding python-jose to pyproject should fail the gate even before `poetry install`."""
    write_pyproject(tmp_path, """
[tool.poetry]
name = "x"
version = "0.0.1"

[tool.poetry.dependencies]
python = ">=3.12,<4.0"
python-jose = "^3.3"
""")
    assert cja.main(str(tmp_path / "pyproject.toml")) == 1


def test_declared_jwt_lib_in_allowlist_passes(tmp_path):
    write_pyproject(tmp_path, """
[tool.poetry]
name = "x"
version = "0.0.1"

[tool.poetry.dependencies]
python = ">=3.12,<4.0"
python-jose = "^3.3"

[tool.mcp-template]
jwt-allowlist = ["python-jose"]
""")
    assert cja.main(str(tmp_path / "pyproject.toml")) == 0


def test_dev_group_jwt_lib_caught(tmp_path):
    """Dev-group JWT deps must also be inspected."""
    write_pyproject(tmp_path, """
[tool.poetry]
name = "x"
version = "0.0.1"

[tool.poetry.dependencies]
python = ">=3.12,<4.0"

[tool.poetry.group.dev.dependencies]
authlib = "^1.0"
""")
    assert cja.main(str(tmp_path / "pyproject.toml")) == 1


def test_allowlist_case_insensitive(tmp_path):
    write_pyproject(tmp_path, """
[tool.poetry]
name = "x"
version = "0.0.1"

[tool.poetry.dependencies]
python = ">=3.12,<4.0"
PyJWT = "^2.0"

[tool.mcp-template]
jwt-allowlist = ["pyjwt"]
""")
    assert cja.main(str(tmp_path / "pyproject.toml")) == 0


def test_transitive_installed_jwt_lib_caught(tmp_path, monkeypatch):
    """Even if pyproject is clean, an installed JWT lib (e.g. pulled transitively
    by an upstream release) without allowlist entry should fail the gate."""
    monkeypatch.setattr(cja, "_installed_deps", lambda: {"python-jose"})
    write_pyproject(tmp_path, """
[tool.poetry]
name = "x"
version = "0.0.1"

[tool.poetry.dependencies]
python = ">=3.12,<4.0"
""")
    assert cja.main(str(tmp_path / "pyproject.toml")) == 1
