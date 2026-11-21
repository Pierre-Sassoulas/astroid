# Assign, AnnAssign, AugAssign.
# +5: position: 7:0-7:7
# +4: targets[0]: AssignName(var)
# +3: targets[0].position: 7:0-7:3
# +2: value: Const(2)
# +1: value.position: 7:6-7:7
var = 2
# +7: annotation: Name(int)
# +6: annotation.position: 15:6-15:9
# +5: position: 15:0-15:13
# +4: target: AssignName(var2)
# +3: target.position: 15:0-15:4
# +2: value: Const(2)
# +1: value.position: 15:12-15:13
var2: int = 2
# +5: position: 21:0-21:9
# +4: target: AssignName(var3)
# +3: target.position: 21:0-21:4
# +2: value: Const(2)
# +1: value.position: 21:8-21:9
var3 += 2
