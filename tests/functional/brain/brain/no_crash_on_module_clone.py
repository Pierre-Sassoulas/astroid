# Test that random.sample does not crash when cloning Module nodes.
#
# Module.__init__ does not accept ``lineno``/``col_offset`` kwargs, so
# cloning must filter init params to those the class actually accepts.
#
# Regression test for https://github.com/pylint-dev/astroid/issues/3043
from random import sample
import gc
# +3: inferred: List(Module(gc))
# +2: inferred.elts[0]: Module(gc)
# +1: inferred.elts[0].name: 'gc'
sample(list({gc}) * 2, 1)
