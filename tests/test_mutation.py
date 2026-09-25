# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Inference of dict, list and set literals mutated before they are used."""

from __future__ import annotations

import pytest

from astroid import bases, extract_node, mutation, nodes, util

UNKNOWN = "?"  # Uninferable in strict mode, an instance of the builtin in opaque mode

# case: (code, off, model, fork)
# strict and opaque are ``model`` where the model is exact, UNKNOWN otherwise.
CASES = {
    "setitem": ("d = {'a': 1}\nd['b'] = 2\nd #@", ["{'a': 1}"], ["{'a': 1, 'b': 2}"], None),
    "update_kw": (
        "d = {'mode': 5}\nd.update(encoding='x')\nd #@",
        ["{'mode': 5}"],
        ["{'mode': 5, 'encoding': 'x'}"],
        None,
    ),
    "update_dict": ("d = {}\nd.update({'a': 1})\nd #@", ["{}"], ["{'a': 1}"], None),
    "pop": ("d = {'a': 1, 'b': 2}\nd.pop('a')\nd #@", ["{'a': 1, 'b': 2}"], ["{'b': 2}"], None),
    "del": ("d = {'a': 1}\ndel d['a']\nd #@", ["{'a': 1}"], ["{}"], None),
    "override": ("d = {'a': 1}\nd['a'] = 3\nd #@", ["{'a': 1}"], ["{'a': 3}"], None),
    "append": ("l = [1]\nl.append(2)\nl.extend([3, 4])\nl #@", ["[1]"], ["[1, 2, 3, 4]"], None),
    "set_add": ("s = {1}\ns.add(2)\ns.add(1)\ns #@", ["{1}"], ["{1, 2}"], None),
    "pure_method": ("d = {'a': 1}\nd.get('a')\nd #@", ["{'a': 1}"], ["{'a': 1}"], None),
    "pure_callee": ("d = {}\nlen(d)\nd['a'] = 1\nd #@", ["{}"], ["{'a': 1}"], None),
    "kwargs_copy": ("d = {}\nf(**d)\nd['a'] = 1\nd #@", ["{}"], ["{'a': 1}"], None),
    "dict_unpack_copy": ("d = {}\ne = {**d}\nd['a'] = 1\nd #@", ["{}"], ["{'a': 1}"], None),
    "use_in_nested_function": (
        "d = {}\nd['a'] = 1\ndef f():\n    return __(d)",
        ["{}"],
        ["{'a': 1}"],
        None,
    ),
    "after_use": ("d = {}\nd #@\nd['a'] = 1", ["{}"], ["{}"], None),
    "rebind": ("d = {'z': 0}\nd['a'] = 1\nd = {}\nd #@", ["{}"], ["{}"], None),
    "exclusive_branch": (
        "d = {}\nif c:\n    d['a'] = 1\nelse:\n    d #@",
        ["{}"],
        ["{}"],
        None,
    ),
    # Unknown to the model from here on.
    "if_branch": (
        "d = {}\nif c:\n    d['a'] = 1\nd #@",
        ["{}"],
        ["{}"],
        ["{}", "{'a': 1}"],
    ),
    "loop_non_const_key": ("d = {}\nfor k in ks:\n    d[k] = 1\nd #@", ["{}"], ["{}"], None),
    "escape_to_call": ("d = {}\nf(d)\nd #@", ["{}"], ["{}"], None),
    "alias": ("d = {}\ne = d\ne['a'] = 1\nd #@", ["{}"], ["{}"], None),
    "unknown_update": ("d = {}\nd.update(g())\nd #@", ["{}"], ["{}"], None),
    "mutated_in_nested_function": (
        "d = {}\ndef reg():\n    d['a'] = 1\nd #@",
        ["{}"],
        ["{}"],
        ["{}", "{'a': 1}"],
    ),
    "while_back_edge": (
        "d = {'a': 1}\nwhile d:\n    d #@\n    d.pop('a')",
        ["{'a': 1}"],
        ["{'a': 1}"],
        ["{'a': 1}", "{}"],
    ),
    "unmodelled_method": ("l = [3, 1]\nl.sort()\nl #@", ["[3, 1]"], ["[3, 1]"], None),
}
_INEXACT = {
    "if_branch",
    "loop_non_const_key",
    "escape_to_call",
    "alias",
    "unknown_update",
    "mutated_in_nested_function",
    "while_back_edge",
    "unmodelled_method",
}
_EXACT = set(CASES) - _INEXACT


def _render(value: object) -> str:
    if isinstance(value, util.UninferableBase):
        return "Uninferable"
    if type(value) is bases.Instance:
        return f"<{value.pytype()}>"
    return value.as_string()


def _infer(code: str) -> list[str]:
    node = extract_node(code)
    return [_render(value) for value in node.infer()]


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("mode", ["off", "model", "fork", "strict", "opaque"])
def test_mutation_modes(monkeypatch: pytest.MonkeyPatch, mode: str, name: str) -> None:
    monkeypatch.setattr(mutation, "MODE", mode)
    code, off, model, fork = CASES[name]
    if mode == "off":
        expected = off
    elif mode == "model":
        expected = model
    elif mode == "fork":
        expected = fork or model
    elif name in _EXACT:
        expected = model
    else:
        monkeypatch.setattr(mutation, "MODE", "off")
        pytype = extract_node(code).inferred()[0].pytype()
        monkeypatch.setattr(mutation, "MODE", mode)
        expected = ["Uninferable"] if mode == "strict" else [f"<{pytype}>"]
    assert _infer(code) == expected


def test_origin_links_replayed_value_to_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mutation, "MODE", "model")
    literal, used = extract_node("d = {} #@\nd['a'] = 1\nd #@")
    replayed = used.inferred()[0]
    assert isinstance(replayed, nodes.Dict)
    assert replayed is not literal.value
    assert mutation.origin(replayed) is literal.value


@pytest.mark.parametrize("mode,expected", [("model", ["{'a': 1}"]), ("strict", ["Uninferable"])])
def test_attribute_store_escapes(
    monkeypatch: pytest.MonkeyPatch, mode: str, expected: list[str]
) -> None:
    """``obj.attr = d`` puts ``d`` under the ``Assign``, not the ``AssignAttr``."""
    monkeypatch.setattr(mutation, "MODE", mode)
    assert _infer("d = {}\nobj.attr = d\nd['a'] = 1\nd #@") == expected
