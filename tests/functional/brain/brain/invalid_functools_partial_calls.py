from functools import partial
from unknown import Unknown

def test(a, b, c):
    return a + b + c

# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial()
# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial(test)
# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial(func=test)
# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial(some_func, a=1)
# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial(Unknown, a=1)
# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial(2, a=1)
# +1: inferred: Instance(_functools.functools.partial) | Instance(functools.partial) | Uninferable
partial(test, unknown=1)
