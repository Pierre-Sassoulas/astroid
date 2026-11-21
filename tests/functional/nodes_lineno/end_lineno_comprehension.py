# ListComp, SetComp, DictComp, GeneratorExpr.
# +4: elt: Name(x)
# +3: elt.position: 6:1-6:2
# +2: generators[0]: Comprehension(for x in var)
# +1: position: 6:0-6:16
[x for x in var]
# +4: elt: Name(x)
# +3: elt.position: 11:1-11:2
# +2: generators[0]: Comprehension(for x in var)
# +1: position: 11:0-11:16
{x for x in var}
# +6: generators[0]: Comprehension(for (x, y) in var)
# +5: key: Name(x)
# +4: key.position: 18:1-18:2
# +3: position: 18:0-18:22
# +2: value: Name(y)
# +1: value.position: 18:4-18:5
{x: y for x, y in var}
# +4: elt: Name(x)
# +3: elt.position: 23:1-23:2
# +2: generators[0]: Comprehension(for x in var)
# +1: position: 23:0-23:16
(x for x in var)
