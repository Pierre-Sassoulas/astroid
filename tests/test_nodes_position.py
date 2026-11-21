# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

from tokenize import TokenError
from unittest import mock

from astroid import builder, nodes


class TestNodePosition:
    """Test node ``position`` attribute."""

    @staticmethod
    def test_position_malformed_tokenize() -> None:
        """A ``TokenError`` from ``tokenize`` must not crash the build.

        On Python < 3.12 malformed source could make ``generate_tokens``
        raise a ``TokenError``; ``position`` is simply unavailable then.
        """
        with mock.patch(
            "astroid.rebuilder.generate_tokens",
            side_effect=TokenError("unexpected EOF in multi-line statement", (1, 0)),
        ):
            node = builder.extract_node("class A:  #@\n    ...")
        assert isinstance(node, nodes.ClassDef)
        assert node.position is None

    @staticmethod
    def test_position_carriage_return_line_endings() -> None:
        """Lines ending in ``\\r`` must not crash the build (#3091).

        The tokenizer treats a lone ``\\r`` as a line terminator while the
        source kept by the rebuilder is split on ``\\n`` only, so the slice
        tokenized for the position can be misaligned and raise
        ``IndentationError``; ``position`` is simply unavailable then.
        """
        module = builder.parse("\rclass C:\n def f():\n  1\n 2")
        klass = module.body[0]
        assert isinstance(klass, nodes.ClassDef)
        func = klass.body[0]
        assert isinstance(func, nodes.FunctionDef)
        assert klass.position is None
        assert func.position is None
