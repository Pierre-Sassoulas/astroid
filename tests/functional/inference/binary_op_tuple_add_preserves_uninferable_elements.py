from missing import Unknown

# +5: inferred: Tuple((Unknown.Unknown(), 1, 2, Unknown.Unknown()))
# +4: inferred.elts[0]: Unknown(Unknown.Unknown())
# +3: inferred.elts[1].value: 1
# +2: inferred.elts[2].value: 2
# +1: inferred.elts[3]: Unknown(Unknown.Unknown())
(Unknown, 1) + (2, Unknown)
