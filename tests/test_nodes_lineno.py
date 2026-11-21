# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt


import astroid
from astroid import nodes


class TestLinenoColOffset:
    """Test 'lineno', 'col_offset', 'end_lineno', and 'end_col_offset' for all
    nodes.
    """

    # fmt: on

    @staticmethod
    def test_end_lineno_call_multiline() -> None:
        """Regression test for https://github.com/pylint-dev/astroid/issues/784.

        ``tolineno`` used to return 2 (the line of the closing ``]``) instead of
        the closing ``)`` line, disagreeing with ``ast.end_lineno``.
        """
        code = '"".join(\n\t["", ""]\n)'
        module = astroid.parse(code)
        call = module.body[0].value
        assert isinstance(call, nodes.Call)
        assert call.tolineno == 3
        assert call.end_lineno == 3

        # fmt: on

        # fmt: on

        # fmt: on

    @staticmethod
    def test_end_lineno_module() -> None:
        """Tests for Module."""
        code = """print()"""
        module = astroid.parse(code)
        assert isinstance(module, nodes.Module)
        assert module.lineno == 0
        assert module.col_offset == 0
        assert module.end_lineno is None
        assert module.end_col_offset is None
