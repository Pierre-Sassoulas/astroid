from random import sample
class A: pass
sample(list({1: A()}.values()), 1)  # inferred: List([A()])  # inferred.elts[0]: Call(A())
