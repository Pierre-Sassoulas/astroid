# Attribute, AssignAttr, DelAttr.
class X:
    var = 42

# +5: position: 10:0-10:10
# +4: targets[0]: AssignAttr(X.var2)
# +3: targets[0].position: 10:0-10:6
# +2: value: Const(2)
# +1: value.position: 10:9-10:10
X.var2 = 2
X.var2  # expr: Name(X)  # expr.position: 11:0-11:1  # position: 11:0-11:6
del X.var2  # position: 12:0-12:10  # targets[0]: DelAttr(X.var2)  # targets[0].position: 12:4-12:10
