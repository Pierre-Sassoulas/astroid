# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import warnings
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar, Union, cast

from astroid.context import _invalidate_cache
from astroid.typing import TransformFn

if TYPE_CHECKING:
    from astroid import nodes

    _NodesT = TypeVar("_NodesT", bound="nodes.NodeNG")
    _Predicate = Callable[[_NodesT], bool] | None

# The values of the _astroid_fields of a node. Tuples come from Dict.items.
# pylint: disable-next=consider-alternative-union-syntax
_Vistables = Union[
    "nodes.NodeNG", list["_Vistables"], tuple["_Vistables", ...], str, None
]


class TransformVisitor:
    """A visitor for handling transforms.

    The standard approach of using it is to call
    :meth:`~visit` with an *astroid* module and the class
    will take care of the rest, walking the tree and running the
    transforms for each encountered node.

    Based on its usage in AstroidManager.brain, it should not be reinstantiated.
    """

    def __init__(self) -> None:
        # The typing here is incorrect, but it's the best we can do
        # Refer to register_transform and unregister_transform for the correct types
        self.transforms: defaultdict[
            type[nodes.NodeNG],
            list[tuple[TransformFn[nodes.NodeNG], _Predicate[nodes.NodeNG]]],
        ] = defaultdict(list)

    def _transform(self, node: nodes.NodeNG) -> nodes.NodeNG:
        """Call matching transforms for the given node if any and return the
        transformed node.
        """
        cls = node.__class__

        for transform_func, predicate in self.transforms[cls]:
            if predicate is None or predicate(node):
                ret = transform_func(node)
                # if the transformation function returns something, it's
                # expected to be a replacement for the node
                if ret is not None:
                    _invalidate_cache()
                    node = ret
                if ret.__class__ != cls:
                    # Can no longer apply the rest of the transforms.
                    break
        return node

    def _visit(self, node: nodes.NodeNG) -> nodes.NodeNG:
        for name in node._astroid_fields:
            value = getattr(node, name)
            if TYPE_CHECKING:
                value = cast(_Vistables, value)

            visited = self._visit_generic(value)
            if visited != value:
                setattr(node, name, visited)
        return self._transform(node)

    def _visit_generic(self, node: _Vistables) -> _Vistables:
        if not node:
            return node
        if isinstance(node, list):
            return [self._visit_generic(child) for child in node]
        if isinstance(node, tuple):
            return tuple(self._visit_generic(child) for child in node)
        if isinstance(node, str):
            return node

        try:
            return self._visit(node)
        except RecursionError:
            # Returning the node untransformed is better than giving up.
            warnings.warn(
                f"Astroid was unable to transform {node}.\n"
                "Some functionality will be missing unless the system recursion limit is lifted.\n"
                "From pylint, try: --init-hook='import sys; sys.setrecursionlimit(2000)' or higher.",
                UserWarning,
                stacklevel=0,
            )
            return node

    def register_transform(
        self,
        node_class: type[_NodesT],
        transform: TransformFn[_NodesT],
        predicate: _Predicate[_NodesT] | None = None,
    ) -> None:
        """Register `transform(node)` function to be applied on the given node.

        The transform will only be applied if `predicate` is None or returns true
        when called with the node as argument.

        The transform function may return a value which is then used to
        substitute the original node in the tree.
        """
        self.transforms[node_class].append((transform, predicate))  # type: ignore[arg-type]

    def unregister_transform(
        self,
        node_class: type[_NodesT],
        transform: TransformFn[_NodesT],
        predicate: _Predicate[_NodesT] | None = None,
    ) -> None:
        """Unregister the given transform."""
        self.transforms[node_class].remove((transform, predicate))  # type: ignore[arg-type]

    def visit(self, node: nodes.NodeNG) -> nodes.NodeNG:
        """Walk the given astroid *tree* and transform each encountered node.

        Only the nodes which have transforms registered will actually
        be replaced or changed.
        """
        return self._visit(node)
