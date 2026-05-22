"""Tests for the no-print() gate."""
from __future__ import annotations

import check_no_print as cnp


def test_print_in_src_fails(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "thing.py").write_text("print('hello')\n")
    assert cnp.main([str(src)]) == 1


def test_clean_src_passes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "thing.py").write_text("import logging\nlog = logging.getLogger(__name__)\nlog.info('ok')\n")
    assert cnp.main([str(src)]) == 0


def test_print_under_tests_subdir_allowed(tmp_path):
    """Test code routinely uses print() for diagnostics. Should not fail the gate
    when the path argument happens to include a tests/ subtree."""
    root = tmp_path
    (root / "src").mkdir()
    (root / "src" / "__init__.py").write_text("")
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text("def test_x():\n    print('debug')\n")
    assert cnp.main([str(root)]) == 0


def test_print_under_fixtures_subdir_allowed(tmp_path):
    """Fixture files demonstrating bad patterns must not fail the gate."""
    root = tmp_path
    fixtures = root / "fixtures"
    fixtures.mkdir()
    (fixtures / "bad_example.py").write_text("print('this is intentional')\n")
    assert cnp.main([str(root)]) == 0
