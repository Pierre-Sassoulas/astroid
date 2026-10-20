# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import Uninferable, extract_node, nodes, parse
from astroid.brain.helpers import is_class_var, register_module_extender
from astroid.manager import AstroidManager


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            """
            from typing import ClassVar

            foo: ClassVar[int]
            """,
            id="from-import",
        ),
        pytest.param(
            """
            from typing import ClassVar

            foo: ClassVar
            """,
            id="bare-classvar",
        ),
        pytest.param(
            """
            import typing

            foo: typing.ClassVar[int]
            """,
            id="module-import",
        ),
    ],
)
def test_is_class_var_returns_true(code):
    node = extract_node(code)
    assert isinstance(node, nodes.AnnAssign)
    assert is_class_var(node.annotation)


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            """
            from typing import Final

            foo: Final[int]
            """,
            id="wrong-name",
        ),
        pytest.param(
            """
            from typing import ClassVar

            foo: list[ClassVar[int]]
            """,
            id="classvar-not-outermost",
        ),
        pytest.param(
            """
            from typing import ClassVar
            ClassVar = int

            foo: ClassVar
            """,
            id="shadowed-name",
        ),
        pytest.param(
            """
            foo: ClassVar[int]
            """,
            id="missing-import",
        ),
        pytest.param(
            """
            import os

            foo: os
            """,
            id="module-annotation",
        ),
    ],
)
def test_is_class_var_returns_false(code):
    node = extract_node(code)
    assert isinstance(node, nodes.AnnAssign)
    assert not is_class_var(node.annotation)


def test_register_module_extender_does_not_reparent_non_node_locals() -> None:
    """Locals of the extension module are copied, but only nodes are reparented."""
    extension_module = parse("def f(): pass")
    extension_module.locals["y"] = [Uninferable]
    transforms = []

    class FakeManager:
        @staticmethod
        def register_transform(node_class, transform, predicate) -> None:
            transforms.append(transform)

    register_module_extender(FakeManager(), "mod", lambda: extension_module)
    module = parse("", module_name="mod")
    transforms[0](module)
    assert module.locals["f"][0].parent is module
    assert module.locals["y"] == [Uninferable]


def test_module_named_class_var_is_not_a_class_var() -> None:
    """Only a class, a function or an instance named ``ClassVar`` is matched."""
    manager = AstroidManager()
    manager.astroid_cache["ClassVar"] = parse("", module_name="ClassVar")
    try:
        node = extract_node("""
        import ClassVar

        foo: ClassVar
        """)
        assert not is_class_var(node.annotation)
    finally:
        del manager.astroid_cache["ClassVar"]
