# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import sys
import types
import unittest
from collections.abc import Iterator

import pytest

try:
    import gi  # pylint: disable=unused-import

    HAS_GI = True
except ImportError:
    HAS_GI = False

from astroid import builder, nodes
from astroid.brain import brain_gi
from astroid.brain.brain_gi import _looks_like_require_version
from astroid.manager import AstroidManager


@unittest.skipUnless(HAS_GI, "This test requires the gobject introspection library.")
class GiBrainClassificationTest(unittest.TestCase):
    """Test that gi functions are correctly classified."""

    def _inferred_gi_symbol(self, namespace, version, symbol):
        node = builder.extract_node(f"""
        import gi

        gi.require_version("{namespace}", "{version}")
        from gi.repository import {namespace}
        {namespace}.{symbol}
        """)
        return node.inferred()

    def test_gi_function_classification(self):
        """Test that global functions are correctly classified without the 'self' argument."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "get_tmp_dir")
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].pytype(), "builtins.function")

        funcdef = inferred[0].frame()
        self.assertIsInstance(funcdef, nodes.FunctionDef)

        args = funcdef.argnames()
        if len(args) > 0:
            self.assertNotEqual(args[0], "self")

    def test_gi_method_classification(self):
        """Test that methods are correctly classified and accept the 'self' argument."""
        inferred = self._inferred_gi_symbol("GLib", "2.0", "String.append")
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0].pytype(), "builtins.instancemethod")

        funcdef = inferred[0].frame()
        self.assertIsInstance(funcdef, nodes.FunctionDef)

        self.assertIn(
            funcdef.argnames()[0],
            {"self", funcdef.args.vararg},
            "Method does not accept 'self' as first argument",
        )


class RequireVersionMatchTest(unittest.TestCase):
    """``_looks_like_require_version`` must only match gi's ``require_version``.

    A match triggers ``import gi`` and ``gi.require_version(...)`` at build time,
    so a false positive runs that side effect for unrelated source. This test
    needs no gi and asserts the predicate, not the side effect.
    """

    @staticmethod
    def _call(source: str) -> nodes.Call:
        call = builder.extract_node(source)
        assert isinstance(call, nodes.Call)
        return call

    def test_bare_name_from_gi_matches(self):
        self.assertTrue(
            _looks_like_require_version(
                self._call(
                    'from gi import require_version\nrequire_version("Gtk", "3.0")'
                )
            )
        )

    def test_star_import_from_gi_matches(self):
        self.assertTrue(
            _looks_like_require_version(
                self._call('from gi import *\nrequire_version("Gtk", "3.0")')
            )
        )

    def test_star_import_shadowed_by_local_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(
                self._call(
                    "from gi import *\n"
                    "def require_version(a, b): return None\n"
                    'require_version("Gtk", "3.0")'
                )
            )
        )

    def test_gi_attribute_matches(self):
        self.assertTrue(
            _looks_like_require_version(
                self._call('import gi\ngi.require_version("Gtk", "3.0")')
            )
        )

    def test_local_function_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(
                self._call(
                    'def require_version(a, b): return None\nrequire_version("Gtk", "3.0")'
                )
            )
        )

    def test_undefined_name_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(self._call('require_version("Gtk", "3.0")'))
        )

    def test_other_module_attribute_does_not_match(self):
        self.assertFalse(
            _looks_like_require_version(
                self._call('import other\nother.require_version("Gtk", "3.0")')
            )
        )


class _FakeGi(types.ModuleType):
    """A stand-in for the gi package, which the CI does not install."""

    class PyGIDeprecationWarning(Warning):
        pass

    class PyGIWarning(Warning):
        pass

    def __init__(self) -> None:
        super().__init__("gi")
        self.required_versions: list[tuple[str, str]] = []

    @staticmethod
    def check_version(version: tuple[int, int, int]) -> None:
        """Pretend to be a pygobject that supports inspect.signature()."""

    def require_version(self, namespace: str, version: str) -> None:
        self.required_versions.append((namespace, version))


@pytest.fixture(name="fake_gi")
def fixture_fake_gi(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeGi]:
    gi_module = _FakeGi()
    monkeypatch.setitem(sys.modules, "gi", gi_module)
    monkeypatch.setattr(brain_gi, "_inspected_modules", {})
    yield gi_module
    AstroidManager().astroid_cache.pop("gi.repository.Fake", None)


def test_stub_built_from_gi_module(
    fake_gi: _FakeGi, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Widget:
        upper = str.upper

    class WidgetError(Exception):
        pass

    def make_widget() -> Widget:
        return Widget()

    repository = types.ModuleType("gi.repository")
    module = types.ModuleType("gi.repository.Fake")
    module.SIZE = 3  # type: ignore[attr-defined]
    module.TITLE = "fake"  # type: ignore[attr-defined]
    module.make_widget = make_widget  # type: ignore[attr-defined]
    module.Widget = Widget  # type: ignore[attr-defined]
    module.WidgetError = WidgetError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gi.repository", repository)
    monkeypatch.setitem(sys.modules, "gi.repository.Fake", module)

    stub = brain_gi._import_gi_module("gi.repository.Fake")

    assert stub.name == "gi.repository.Fake"
    size = stub["SIZE"]
    assert isinstance(size, nodes.AssignName)
    assert size.statement().value.value == 3
    title = stub["TITLE"]
    assert isinstance(title, nodes.AssignName)
    assert title.statement().value.value == "fake"
    assert isinstance(stub["make_widget"], nodes.FunctionDef)
    widget = stub["Widget"]
    assert isinstance(widget, nodes.ClassDef)
    assert [arg.name for arg in widget["upper"].args.args] == ["self"]
    assert [base.as_string() for base in stub["WidgetError"].bases] == ["Exception"]
    # The stub is built once
    assert brain_gi._import_gi_module("gi.repository.Fake") is stub


def test_building_require_version_calls_gi(fake_gi: _FakeGi) -> None:
    builder.parse('import gi\ngi.require_version("Gtk", "3.0")')
    assert fake_gi.required_versions == [("Gtk", "3.0")]
