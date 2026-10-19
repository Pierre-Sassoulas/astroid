# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

import pytest

from astroid import bases, builder, nodes
from astroid.brain.brain_typing import (
    infer_typing_attr,
    infer_typing_typevar_or_newtype,
)
from astroid.exceptions import UseInferenceDefault


def test_infer_typevar() -> None:
    """
    Regression test for: https://github.com/pylint-dev/pylint/issues/8802

    Test that an inferred `typing.TypeVar()` call produces a `nodes.ClassDef`
    node.
    """
    call_node = builder.extract_node("""
    from typing import TypeVar
    TypeVar('My.Type')
    """)
    inferred = next(call_node.infer())
    assert isinstance(inferred, nodes.ClassDef)
    assert inferred.name == "My.Type"


def test_infer_typevar_name_injection() -> None:
    """A crafted TypeVar name must not be spliced into the synthesized class."""
    call_node = builder.extract_node("""
    from typing import TypeVar
    TypeVar('T(EvilBase): #')
    """)
    inferred = next(call_node.infer())
    assert isinstance(inferred, nodes.ClassDef)
    # The name is kept verbatim instead of parsed, so no base is injected.
    assert inferred.name == "T(EvilBase): #"
    assert inferred.bases == []


@pytest.mark.parametrize(
    "code",
    [
        "from unknown_module import TypeVar",
        "def TypeVar(name): ...",
    ],
)
def test_typevar_not_from_typing(code: str) -> None:
    """A TypeVar() call is left to normal inference unless TypeVar is typing's."""
    call_node = builder.extract_node(f"""
    {code}
    TypeVar('T')  #@
    """)
    with pytest.raises(UseInferenceDefault):
        next(infer_typing_typevar_or_newtype(call_node))


def test_uninferable_subscript_is_not_typing() -> None:
    """A subscript of an uninferable name is left to normal inference."""
    subscript = builder.extract_node("""
    from unknown_module import List
    List[int]  #@
    """)
    with pytest.raises(UseInferenceDefault):
        next(infer_typing_attr(subscript))


class TestTypingAlias:
    def test_infer_typing_alias(self) -> None:
        """
        Test that _alias() calls can be inferred.
        """
        node = builder.extract_node("""
            from typing import _alias
            x = _alias(int, float)
            """)
        assert isinstance(node, nodes.Assign)
        assert isinstance(node.value, nodes.Call)
        inferred = next(node.value.infer())
        assert isinstance(inferred, nodes.ClassDef)
        assert len(inferred.bases) == 1
        assert inferred.bases[0].name == "int"

    @pytest.mark.parametrize(
        "alias_args",
        [
            "",  # two missing arguments
            "int",  # one missing argument
            "int, float, tuple",  # one additional argument
        ],
    )
    def test_infer_typing_alias_incorrect_number_of_arguments(
        self, alias_args: str
    ) -> None:
        """
        Regression test for: https://github.com/pylint-dev/astroid/issues/2513

        Test that _alias() calls with the incorrect number of arguments can be inferred.
        """
        node = builder.extract_node(f"""
            from typing import _alias
            x = _alias({alias_args})
            """)
        assert isinstance(node, nodes.Assign)
        assert isinstance(node.value, nodes.Call)
        inferred = next(node.value.infer())
        assert isinstance(inferred, bases.Instance)
        assert inferred.name == "_SpecialGenericAlias"


class TestSpecialAlias:
    @pytest.mark.parametrize(
        "code",
        [
            "_CallableType()",
            "_TupleType()",
        ],
    )
    def test_special_alias_no_crash_on_empty_args(self, code: str) -> None:
        """
        Regression test for: https://github.com/pylint-dev/astroid/issues/2772

        Test that _CallableType() and _TupleType() calls with no arguments
        do not cause an IndexError.
        """
        # Should not raise IndexError
        module = builder.parse(code)
        assert isinstance(module, nodes.Module)
