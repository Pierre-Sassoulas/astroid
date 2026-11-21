# +10: inferred: Tuple((ValueError, TypeError))
# +9: inferred.as_string().strip(): '(ValueError, TypeError)'
# +8: inferred.elts[0]: EvaluatedObject(ValueError)
# +7: inferred.elts[0].inferred: ClassDef(builtins.ValueError)
# +6: inferred.elts[0].value: ClassDef(builtins.ValueError)
# +5: inferred.elts[0].value.name: 'ValueError'
# +4: inferred.elts[1]: EvaluatedObject(TypeError)
# +3: inferred.elts[1].inferred: ClassDef(builtins.TypeError)
# +2: inferred.elts[1].value: ClassDef(builtins.TypeError)
# +1: inferred.elts[1].value.name: 'TypeError'
tuple([ValueError, TypeError])
