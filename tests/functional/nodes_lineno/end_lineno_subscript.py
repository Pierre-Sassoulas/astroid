# Subscript, Slice, (ExtSlice, Index).
# +5: position: 7:0-7:6
# +4: slice: Const(0)
# +3: slice.position: 7:4-7:5
# +2: value: Name(var)
# +1: value.position: 7:0-7:3
var[0]
# +8: position: 16:0-16:10
# +7: slice: Slice(1:2:1)
# +6: slice.lower: Const(1)
# +5: slice.lower.position: 16:4-16:5
# +4: slice.step: Const(1)
# +3: slice.step.position: 16:8-16:9
# +2: slice.upper: Const(2)
# +1: slice.upper.position: 16:6-16:7
var[1:2:1]
var[1:2, 2]  # position: 17:0-17:11  # slice: Tuple((1:2, 2))  # slice.position: 17:4-17:10
