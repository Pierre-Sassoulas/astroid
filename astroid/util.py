# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt


from __future__ import annotations

import re
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final, Literal

from astroid.exceptions import InferenceError

if TYPE_CHECKING:
    from astroid import bases, nodes
    from astroid.context import InferenceContext
    from astroid.nodes.as_string import AsStringVisitor
    from astroid.typing import InferenceResult


class UninferableBase:
    """Special inference object, which is returned when inference fails.

    This is meant to be used as a singleton. Use astroid.util.Uninferable to access it.
    """

    def __repr__(self) -> Literal["Uninferable"]:
        return "Uninferable"

    __str__ = __repr__

    # Uninferable answers any attribute, most of them with itself. Typing the
    # result as UninferableBase is stricter but flags many call sites that
    # handle InferenceResult unions, so keep Any for now.
    def __getattribute__(self, name: str) -> Any:  # type: ignore[explicit-any]
        if name == "next":
            raise AttributeError("next method should not be called")
        if name.startswith("__") and name.endswith("__"):
            return object.__getattribute__(self, name)
        if name == "accept":
            return object.__getattribute__(self, name)
        return self

    def __call__(self, *args: object, **kwargs: object) -> UninferableBase:
        return self

    def __bool__(self) -> Literal[False]:
        return False

    def accept(self, visitor: AsStringVisitor) -> str:
        return visitor.visit_uninferable(self)


Uninferable: Final = UninferableBase()

# Width/precision in a format spec drive how large a formatted string gets.
# Match the leading width and the optional ``.precision`` from the start of a
# format spec (PEP 3101 / format mini-language).
_FORMAT_SPEC_SIZE = re.compile(
    r"(?:.?[<>=^])?[-+ ]?z?#?0?(?P<width>\d+)?(?:[,_])?(?:\.(?P<precision>\d+))?"
)
# Mirrors the sequence/repetition caps in astroid.protocols.
MAX_FORMATTED_SIZE = 10**8


def format_spec_too_large(format_spec: str) -> bool:
    """Whether a format spec asks for an oversized width or precision.

    Used to avoid materializing a multi-gigabyte string while inferring a tiny
    literal such as ``"{:>2000000000}".format("x")`` or ``f"{1.5:.2e9f}"``.
    """
    # Every group in _FORMAT_SPEC_SIZE is optional, so match is never None.
    match = _FORMAT_SPEC_SIZE.match(format_spec)
    assert match is not None
    return any(
        size is not None and int(size) > MAX_FORMATTED_SIZE
        for size in match.group("width", "precision")
    )


class BadOperationMessage:
    """Object which describes a TypeError occurred somewhere in the inference chain.

    This is not an exception, but a container object which holds the types and
    the error which occurred.
    """


class BadUnaryOperationMessage(BadOperationMessage):
    """Object which describes operational failures on UnaryOps."""

    def __init__(self, operand: InferenceResult, op: str, error: Exception) -> None:
        self.operand = operand
        self.op = op
        self.error = error

    @property
    def _object_type_helper(
        self,
    ) -> Callable[[InferenceResult], InferenceResult | None]:
        from astroid import helpers  # pylint: disable=import-outside-toplevel

        return helpers.object_type

    def _object_type(self, obj: InferenceResult) -> InferenceResult | None:
        objtype = self._object_type_helper(obj)
        if isinstance(objtype, UninferableBase):
            return None

        return objtype

    def __str__(self) -> str:
        # Nodes, proxies and Uninferable all expose ``name`` differently (proxies
        # through ``__getattr__``), so it is looked up dynamically. No inferred
        # object has a ``None`` name.
        operand_type = getattr(self.operand, "name", None)
        if operand_type is None:
            object_type = self._object_type(self.operand)
            # Only nameless operands get here (slices for instance), and their
            # type is always known.
            assert object_type is not None
            operand_type = getattr(object_type, "name", None)
            if operand_type is None:
                # Just fallback to as_string
                operand_type = object_type.as_string()

        msg = "bad operand type for unary {}: {}"
        return msg.format(self.op, operand_type)


class BadBinaryOperationMessage(BadOperationMessage):
    """Object which describes type errors for BinOps."""

    def __init__(
        self,
        left_type: InferenceResult | None,
        op: str,
        right_type: InferenceResult | None,
    ) -> None:
        self.left_type = left_type
        self.right_type = right_type
        self.op = op

    def __str__(self) -> str:
        # The types are classes, proxies or Uninferable, which all have a name.
        left_name = getattr(self.left_type, "name", None)
        right_name = getattr(self.right_type, "name", None)
        return (
            f"unsupported operand type(s) for {self.op}: {left_name!r} "
            f"and {right_name!r}"
        )


def check_warnings_filter() -> bool:
    """Return True if any other than the default DeprecationWarning filter is enabled.

    https://docs.python.org/3/library/warnings.html#default-warning-filter
    """
    return any(
        issubclass(DeprecationWarning, filter[2])
        and filter[0] != "ignore"
        and filter[3] != "__main__"
        for filter in warnings.filters
    )


def safe_infer(
    node: nodes.NodeNG | bases.Proxy | UninferableBase,
    context: InferenceContext | None = None,
) -> InferenceResult | None:
    """Return the inferred value for the given node.

    Return None if inference failed or if there is some ambiguity (more than
    one node has been inferred).
    """
    if isinstance(node, UninferableBase):
        return node
    try:
        inferit = node.infer(context=context)
        value = next(inferit)
    except (InferenceError, StopIteration):
        return None
    try:
        next(inferit)
        return None  # None if there is ambiguity on the inferred node
    except InferenceError:
        return None  # there is some kind of ambiguity
    except StopIteration:
        return value
