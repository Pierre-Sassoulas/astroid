# BinOp, BoolOp, UnaryOp, Compare.
# +5: left: Name(x)
# +4: left.position: 7:0-7:1
# +3: position: 7:0-7:5
# +2: right: Name(y)
# +1: right.position: 7:4-7:5
x + y
# +5: position: 13:0-13:7
# +4: values[0]: Name(a)
# +3: values[0].position: 13:0-13:1
# +2: values[1]: Name(b)
# +1: values[1].position: 13:6-13:7
a and b
-var  # operand: Name(var)  # operand.position: 14:1-14:4  # position: 14:0-14:4
# +5: left: Name(a)
# +4: left.position: 20:0-20:1
# +3: ops[0][1]: Name(b)
# +2: ops[0][1].position: 20:4-20:5
# +1: position: 20:0-20:5
a < b
