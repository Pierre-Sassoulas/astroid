a = (1,)
b = (22,)
some = a + b  # inferred: Tuple((1, 22))  # inferred.elts[0].value: 1  # inferred.elts[1].value: 22
