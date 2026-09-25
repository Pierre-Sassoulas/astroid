# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Account for in-place mutations of dict, list and set literals bound to a name.

EXPLORATION PROTOTYPE. The behavior is selected by the ``ASTROID_MUTATION``
environment variable:

* ``off``: no change, the literal is inferred as written.
* ``model``: apply mutations that certainly run before the use and that we know
  how to replay (``d[k] = v``, ``d.update(...)``, ``l.append(x)``...). Everything
  else is ignored, so this never adds ``Uninferable``.
* ``fork``: ``model``, and a replayable mutation that may or may not run yields
  both the mutated and the untouched value.
* ``strict``: ``model``, and any other mutation or escape (unknown method, the
  name passed to a call, aliased, mutated in a nested scope...) makes the value
  ``Uninferable``.
* ``opaque``: ``strict``, but the value becomes an instance of ``dict``,
  ``list`` or ``set`` with unknown contents instead of ``Uninferable``: the
  type survives, the literal does not.

A replayed value is a new node; ``origin()`` gives back the literal it was
replayed from, for checks that compare objects by identity.
"""

from __future__ import annotations

import enum
import itertools
import os
from collections.abc import Iterator
from dataclasses import dataclass

from astroid import nodes
from astroid.const import Context
from astroid.context import InferenceContext, copy_context
from astroid.typing import InferenceResult
from astroid.util import Uninferable, UninferableBase, safe_infer

MODE = os.environ.get("ASTROID_MUTATION", "off")
if MODE not in {"off", "model", "fork", "strict", "opaque"}:
    raise ValueError(f"Unknown ASTROID_MUTATION mode {MODE!r}")

MAX_FORKED_SITES = 3

_MUTABLE_LITERALS = (nodes.Dict, nodes.List, nodes.Set)

_PURE_METHODS = {
    nodes.Dict: {"get", "keys", "values", "items", "copy", "fromkeys"},
    nodes.List: {"index", "count", "copy"},
    nodes.Set: {
        "copy",
        "union",
        "intersection",
        "difference",
        "symmetric_difference",
        "issubset",
        "issuperset",
        "isdisjoint",
    },
}
_DUNDER_PURE = {"__getitem__", "__contains__", "__len__", "__iter__", "__repr__"}

# Builtins that only read their arguments, so passing the name is not an escape.
_PURE_CALLEES = {
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "frozenset",
    "hash",
    "id",
    "isinstance",
    "iter",
    "len",
    "list",
    "max",
    "min",
    "print",
    "repr",
    "reversed",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "type",
    "zip",
}


class SiteKind(enum.Enum):
    METHOD = "method"  # name.attr(...)
    SUBSCRIPT_STORE = "subscript_store"  # name[k] = v
    SUBSCRIPT_DEL = "subscript_del"  # del name[k]
    OPAQUE = "opaque"  # a mutation we never replay (name[k] += v, name.attr kept)
    ESCAPE = "escape"  # the object leaves our sight: f(name), e = name, [name]


@dataclass(frozen=True)
class Site:
    kind: SiteKind
    name_node: nodes.Name
    statement: nodes.NodeNG
    # METHOD: the Call; SUBSCRIPT_*: the Subscript
    node: nodes.NodeNG | None = None


def _classify(name_node: nodes.Name) -> Site | None:
    """Return the mutation site this load of a name is part of, if any."""
    parent = name_node.parent
    statement = name_node.statement()
    if isinstance(parent, nodes.Attribute) and parent.expr is name_node:
        call = parent.parent
        if isinstance(call, nodes.Call) and call.func is parent:
            return Site(SiteKind.METHOD, name_node, statement, call)
        # A bound method taken for later (``add = seen.add``) may mutate anytime.
        return Site(SiteKind.OPAQUE, name_node, statement, parent)
    if isinstance(parent, nodes.Subscript) and parent.value is name_node:
        if isinstance(parent.parent, nodes.AugAssign):
            return Site(SiteKind.OPAQUE, name_node, statement, parent)
        if parent.ctx == Context.Store:
            return Site(SiteKind.SUBSCRIPT_STORE, name_node, statement, parent)
        if parent.ctx == Context.Del:
            return Site(SiteKind.SUBSCRIPT_DEL, name_node, statement, parent)
        return None
    if isinstance(parent, nodes.Call) and name_node in parent.args:
        if isinstance(parent.func, nodes.Name) and parent.func.name in _PURE_CALLEES:
            return None
        return Site(SiteKind.ESCAPE, name_node, statement, parent)
    if isinstance(parent, nodes.Keyword):
        # ``f(**name)`` copies the items, the object itself is not passed.
        if parent.arg is None:
            return None
        if isinstance(parent.parent, nodes.Call) and isinstance(
            parent.parent.func, nodes.Name
        ) and parent.parent.func.name in _PURE_CALLEES:
            return None
        return Site(SiteKind.ESCAPE, name_node, statement, parent)
    if isinstance(parent, (nodes.Assign, nodes.AnnAssign)):
        if parent.value is name_node:
            return Site(SiteKind.ESCAPE, name_node, statement, parent)
        return None
    if isinstance(parent, (nodes.List, nodes.Tuple, nodes.Set, nodes.Yield)):
        return Site(SiteKind.ESCAPE, name_node, statement, parent)
    if isinstance(parent, nodes.Dict):
        # ``{**name}`` copies the items, the object itself is not kept.
        if any(
            value is name_node and isinstance(key, nodes.DictUnpack)
            for key, value in parent.items
        ):
            return None
        return Site(SiteKind.ESCAPE, name_node, statement, parent)
    return None


def _sites_index(
    root: nodes.Module,
) -> dict[tuple[nodes.LocalsDictNodeNG, str], list[Site]]:
    """Map (frame that binds the name, name) to the mutation sites of the name.

    Built once per module: most names have no site, which keeps inference fast.
    """
    index = root.__dict__.get("_astroid_mutation_sites")
    if index is not None:
        return index
    index = {}
    root.__dict__["_astroid_mutation_sites"] = index
    for name_node in root.nodes_of_class(nodes.Name):
        site = _classify(name_node)
        if site is None:
            continue
        frame, stmts = name_node.lookup(name_node.name)
        if not stmts:
            continue
        index.setdefault((frame, name_node.name), []).append(site)
    return index


def _position(node: nodes.NodeNG) -> tuple[int, int] | None:
    if node.lineno is None or node.col_offset is None:
        return None
    return (node.lineno, node.col_offset)


def _loops_containing(node: nodes.NodeNG, stop: nodes.NodeNG) -> list[nodes.NodeNG]:
    """Loops between ``node`` and ``stop`` whose body is re-run around ``node``."""
    loops = []
    child = node
    for parent in node.node_ancestors():
        if parent is stop:
            break
        if isinstance(parent, (nodes.For, nodes.While)):
            # The iterable of a for loop is evaluated once, before any iteration.
            if not (isinstance(parent, nodes.For) and child is parent.iter):
                loops.append(parent)
        elif isinstance(parent, nodes.Comprehension) and child is not parent.iter:
            loops.append(parent)
        child = parent
    return loops


_CONDITIONAL = (
    nodes.If,
    nodes.IfExp,
    nodes.BoolOp,
    nodes.Try,
    nodes.TryStar,
    nodes.For,
    nodes.While,
    nodes.Match,
    nodes.Comprehension,
    nodes.Lambda,
    nodes.FunctionDef,
    nodes.AsyncFunctionDef,
    nodes.ClassDef,
)


def _is_unconditional(site: Site, use: nodes.Name) -> bool:
    """Whether the site runs on every path to the use, once it runs at all.

    Walk up from the site to the first ancestor that also contains the use;
    any branch or loop on the way makes the site conditional. For a
    ``try``/``if`` that contains both, the site is on the use's own path.
    """
    for ancestor in site.name_node.node_ancestors():
        if ancestor.parent_of(use):
            return True
        if isinstance(ancestor, _CONDITIONAL):
            return False
    return False


@dataclass(frozen=True)
class _Relevant:
    site: Site
    unconditional: bool


def _relevant_sites(
    sites: list[Site],
    binding: nodes.NodeNG,
    use: nodes.Name,
    frame: nodes.LocalsDictNodeNG,
) -> Iterator[_Relevant] | None:
    """Sites that may run between the binding of the name and the use.

    Return None when positions are missing and nothing can be said.
    """
    binding_statement = binding.statement()
    binding_pos = _position(binding_statement)
    use_statement = use.statement()
    use_pos = _position(use_statement)
    if binding_pos is None or use_pos is None:
        return None
    use_in_nested_scope = use.scope() is not frame
    relevant = []
    for site in sites:
        site_pos = _position(site.statement)
        if site_pos is None:
            return None
        if site.statement is use_statement:
            continue
        if nodes.are_exclusive(site.statement, use_statement) or nodes.are_exclusive(
            site.statement, binding_statement
        ):
            continue
        site_in_frame = site.name_node.scope() is frame
        if not site_in_frame:
            # Mutated from a nested function: may have run whenever it was called.
            relevant.append(_Relevant(site, unconditional=False))
            continue
        after_binding = site_pos > binding_pos or binding_statement.parent_of(
            site.statement
        )
        if not after_binding:
            continue
        if use_in_nested_scope:
            # The nested function usually runs once the enclosing frame is done.
            relevant.append(
                _Relevant(site, unconditional=not _in_branch_or_loop(site, frame))
            )
            continue
        if site_pos < use_pos:
            back_edge = False
        else:
            back_edge = any(
                loop.parent_of(use) and not loop.parent_of(binding_statement)
                for loop in _loops_containing(site.name_node, frame)
            )
            if not back_edge:
                continue
        relevant.append(
            _Relevant(
                site, unconditional=not back_edge and _is_unconditional(site, use)
            )
        )
    return iter(relevant)


def _in_branch_or_loop(site: Site, frame: nodes.NodeNG) -> bool:
    for ancestor in site.name_node.node_ancestors():
        if ancestor is frame:
            return False
        if isinstance(ancestor, _CONDITIONAL):
            return True
    return False


# ---------------------------------------------------------------------------
# Replaying mutations on a copy of the literal.
# ---------------------------------------------------------------------------


class _CannotReplay(Exception):
    pass


def _const_value(node: nodes.NodeNG, context: InferenceContext) -> object:
    inferred = safe_infer(node, context=context)
    if not isinstance(inferred, nodes.Const):
        raise _CannotReplay
    return inferred.value


def _dict_key_values(
    items: list[tuple[InferenceResult, InferenceResult]], context: InferenceContext
) -> list[object]:
    return [_const_value(key, context) for key, _ in items]


def _dict_set(items, key_node, key, value, context) -> None:
    keys = _dict_key_values(items, context)
    for index, existing in enumerate(keys):
        if existing == key:
            items[index] = (items[index][0], value)
            return
    items.append((key_node, value))


def _dict_del(items, key, context) -> None:
    keys = _dict_key_values(items, context)
    items[:] = [item for item, existing in zip(items, keys) if existing != key]


def _replay_dict(
    items: list, site: Site, context: InferenceContext
) -> None:
    if site.kind is SiteKind.SUBSCRIPT_STORE:
        subscript = site.node
        assign = subscript.parent
        if not isinstance(assign, nodes.Assign) or len(assign.targets) != 1:
            raise _CannotReplay
        key = _const_value(subscript.slice, context)
        _dict_set(items, subscript.slice, key, assign.value, context)
        return
    if site.kind is SiteKind.SUBSCRIPT_DEL:
        _dict_del(items, _const_value(site.node.slice, context), context)
        return
    call: nodes.Call = site.node
    method = call.func.attrname
    if method in _PURE_METHODS[nodes.Dict] or method in _DUNDER_PURE:
        return
    if any(isinstance(arg, nodes.Starred) for arg in call.args) or call.kwargs:
        raise _CannotReplay
    if method == "update":
        if len(call.args) > 1:
            raise _CannotReplay
        if call.args:
            other = safe_infer(call.args[0], context=context)
            if not isinstance(other, nodes.Dict):
                raise _CannotReplay
            for key_node, value in other.items:
                _dict_set(items, key_node, _const_value(key_node, context), value, context)
        for keyword in call.keywords:
            key_node = nodes.Const(keyword.arg, parent=keyword)
            _dict_set(items, key_node, keyword.arg, keyword.value, context)
        return
    if method in {"pop", "setdefault"} and call.args and not call.keywords:
        key = _const_value(call.args[0], context)
        if method == "pop":
            _dict_del(items, key, context)
            return
        if key not in _dict_key_values(items, context):
            default = call.args[1] if len(call.args) > 1 else nodes.Const(None, parent=call)
            items.append((call.args[0], default))
        return
    if method == "popitem" and not call.args and items:
        items.pop()
        return
    if method == "clear" and not call.args:
        items.clear()
        return
    raise _CannotReplay


def _elements_of(node: nodes.NodeNG, context: InferenceContext) -> list:
    inferred = safe_infer(node, context=context)
    if not isinstance(inferred, (nodes.List, nodes.Tuple)):
        raise _CannotReplay
    if any(isinstance(elt, nodes.Starred) for elt in inferred.elts):
        raise _CannotReplay
    return list(inferred.elts)


def _replay_list(elts: list, site: Site, context: InferenceContext) -> None:
    if site.kind in {SiteKind.SUBSCRIPT_STORE, SiteKind.SUBSCRIPT_DEL}:
        subscript = site.node
        index = _const_value(subscript.slice, context)
        if not isinstance(index, int) or not -len(elts) <= index < len(elts):
            raise _CannotReplay
        if site.kind is SiteKind.SUBSCRIPT_DEL:
            del elts[index]
            return
        assign = subscript.parent
        if not isinstance(assign, nodes.Assign) or len(assign.targets) != 1:
            raise _CannotReplay
        elts[index] = assign.value
        return
    call: nodes.Call = site.node
    method = call.func.attrname
    if method in _PURE_METHODS[nodes.List] or method in _DUNDER_PURE:
        return
    if call.keywords or any(isinstance(arg, nodes.Starred) for arg in call.args):
        raise _CannotReplay
    args = call.args
    if method == "append" and len(args) == 1:
        elts.append(args[0])
    elif method == "extend" and len(args) == 1:
        elts.extend(_elements_of(args[0], context))
    elif method == "insert" and len(args) == 2:
        index = _const_value(args[0], context)
        if not isinstance(index, int):
            raise _CannotReplay
        elts.insert(index, args[1])
    elif method == "pop" and not args and elts:
        elts.pop()
    elif method == "pop" and len(args) == 1:
        index = _const_value(args[0], context)
        if not isinstance(index, int) or not -len(elts) <= index < len(elts):
            raise _CannotReplay
        del elts[index]
    elif method == "clear" and not args:
        elts.clear()
    elif method == "reverse" and not args:
        elts.reverse()
    elif method == "remove" and len(args) == 1:
        target = _const_value(args[0], context)
        values = [_const_value(elt, context) for elt in elts]
        if target not in values:
            raise _CannotReplay
        del elts[values.index(target)]
    else:
        raise _CannotReplay


def _replay_set(elts: list, site: Site, context: InferenceContext) -> None:
    if site.kind is not SiteKind.METHOD:
        raise _CannotReplay
    call: nodes.Call = site.node
    method = call.func.attrname
    if method in _PURE_METHODS[nodes.Set] or method in _DUNDER_PURE:
        return
    if call.keywords or any(isinstance(arg, nodes.Starred) for arg in call.args):
        raise _CannotReplay
    args = call.args
    values = [_const_value(elt, context) for elt in elts]
    if method == "add" and len(args) == 1:
        if _const_value(args[0], context) not in values:
            elts.append(args[0])
    elif method == "update":
        for arg in args:
            for elt in _elements_of(arg, context):
                if _const_value(elt, context) not in values:
                    values.append(_const_value(elt, context))
                    elts.append(elt)
    elif method in {"discard", "remove"} and len(args) == 1:
        target = _const_value(args[0], context)
        if target in values:
            del elts[values.index(target)]
        elif method == "remove":
            raise _CannotReplay
    elif method == "clear" and not args:
        elts.clear()
    else:
        raise _CannotReplay


def _copy_literal(value: nodes.NodeNG) -> nodes.NodeNG:
    new = type(value)(
        lineno=value.lineno,
        col_offset=value.col_offset,
        parent=value.parent,
        end_lineno=value.end_lineno,
        end_col_offset=value.end_col_offset,
    )
    if isinstance(value, nodes.Dict):
        new.postinit(list(value.items))
    else:
        new.postinit(list(value.elts))
    new.__dict__["_astroid_mutation_origin"] = origin(value)
    return new


def origin(value: InferenceResult) -> InferenceResult:
    """The literal a replayed value comes from, or the value itself."""
    if isinstance(value, nodes.NodeNG):
        return value.__dict__.get("_astroid_mutation_origin", value)
    return value


def _unknown_contents(value: nodes.NodeNG) -> InferenceResult:
    if MODE == "opaque":
        # pylint: disable-next=import-outside-toplevel
        from astroid.bases import Instance

        instance = Instance(value._proxied)
        instance.__dict__["_astroid_mutation_origin"] = origin(value)
        return instance
    return Uninferable


def _replay(
    value: nodes.NodeNG, sites: list[Site], context: InferenceContext
) -> nodes.NodeNG:
    new = _copy_literal(value)
    for site in sites:
        if site.kind in {SiteKind.OPAQUE, SiteKind.ESCAPE}:
            raise _CannotReplay
        if isinstance(new, nodes.Dict):
            _replay_dict(new.items, site, context)
        elif isinstance(new, nodes.List):
            _replay_list(new.elts, site, context)
        else:
            _replay_set(new.elts, site, context)
    return new


def _is_pure(site: Site, value: nodes.NodeNG) -> bool:
    if site.kind is not SiteKind.METHOD:
        return False
    method = site.node.func.attrname
    return method in _PURE_METHODS[type(value)] or method in _DUNDER_PURE


def apply_mutations(
    value: InferenceResult,
    binding: nodes.NodeNG,
    use: nodes.Name,
    frame: nodes.LocalsDictNodeNG,
    context: InferenceContext | None,
) -> Iterator[InferenceResult]:
    """Yield what ``value``, bound by ``binding``, may be at ``use``."""
    if MODE == "off" or type(value) not in _MUTABLE_LITERALS:
        yield value
        return
    sites = _sites_index(use.root()).get((frame, use.name))
    if not sites:
        yield value
        return
    relevant = _relevant_sites(sites, binding, use, frame)
    if relevant is None:
        yield value
        return
    relevant = [r for r in relevant if not _is_pure(r.site, value)]
    if not relevant:
        yield value
        return
    replay_context = copy_context(context)
    replay_context.lookupname = None
    unconditional = [r.site for r in relevant if r.unconditional]
    conditional = [r.site for r in relevant if not r.unconditional]
    if MODE in {"strict", "opaque"}:
        try:
            base = _replay(value, unconditional, replay_context)
        except _CannotReplay:
            yield _unknown_contents(value)
            return
    else:
        # model / fork: replay what we can, ignore the rest.
        base = _replay_skipping(value, unconditional, replay_context)
    if not conditional:
        yield base
        return
    if MODE == "model":
        yield base
        return
    if MODE in {"strict", "opaque"}:
        yield _unknown_contents(value)
        return
    # fork
    replayable = [s for s in conditional if s.kind not in {SiteKind.OPAQUE, SiteKind.ESCAPE}]
    if len(replayable) > MAX_FORKED_SITES:
        yield base
        return
    yield base
    for size in range(1, len(replayable) + 1):
        for subset in itertools.combinations(replayable, size):
            try:
                variant = _replay(base, list(subset), replay_context)
            except _CannotReplay:
                continue
            yield variant


def _replay_skipping(
    value: nodes.NodeNG, sites: list[Site], context: InferenceContext
) -> nodes.NodeNG:
    """Replay each site in order, skipping those that cannot be replayed."""
    current = value
    for site in sites:
        try:
            current = _replay(current, [site], context)
        except _CannotReplay:
            continue
    return current
