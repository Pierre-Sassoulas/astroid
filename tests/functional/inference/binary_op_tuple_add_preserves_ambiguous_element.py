def choose():
    value = 1
    if value < 0:
        value = -value
    return value

# +2: inferred: Tuple((0, Unknown.Unknown(), 2))
# +1: inferred.elts[1]: Unknown(Unknown.Unknown())
(0, choose()) + (2,)
