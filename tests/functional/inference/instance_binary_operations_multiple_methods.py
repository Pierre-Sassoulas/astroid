class A(object):
    def __mul__(self, other):
        return 42
class B(A):
    def __mul__(self, other):
        return [42]
a = B()
b = B()
sub = a - b  # inferred: Uninferable
mul = a * b  # inferred: List([42])  # inferred.elts[0]: Const(42)  # inferred.elts[0].value: 42
