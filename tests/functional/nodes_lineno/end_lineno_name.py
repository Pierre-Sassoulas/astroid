# Name, Assign, AssignName, Delete, DelName.
# +5: position: 7:0-7:8
# +4: targets[0]: AssignName(var)
# +3: targets[0].position: 7:0-7:3
# +2: value: Const(42)
# +1: value.position: 7:6-7:8
var = 42
var  # position: 8:0-8:3
del var  # position: 9:0-9:7  # targets[0]: DelName(var)  # targets[0].position: 9:4-9:7

var2 = (  # position: 11:0-13:1  # targets[0]: AssignName(var2)  # targets[0].position: 11:0-11:4
    1, 2, 3
)
