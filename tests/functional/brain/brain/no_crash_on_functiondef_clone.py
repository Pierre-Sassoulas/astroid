# Test that random.sample does not crash when cloning FunctionDef nodes.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/2923
import random
# +3: inferred: List(FunctionDef(no_crash_on_functiondef_clone.len))
# +2: inferred.elts[0]: FunctionDef(no_crash_on_functiondef_clone.len)
# +1: inferred.elts[0].name: 'len'
random.sample([len] * 2, 1)
