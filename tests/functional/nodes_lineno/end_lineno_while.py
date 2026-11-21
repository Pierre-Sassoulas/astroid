# While.
# +11: block_range(1): [1, 16]
# +10: block_range(2): [2, 16]
# +9: block_range(3): [3, 16]
# +8: block_range(4): [4, 16]
# +7: body[0]: Pass(pass)
# +6: body[0].position: 14:4-14:8
# +5: orelse[0]: Pass(pass)
# +4: orelse[0].position: 16:4-16:8
# +3: position: 13:0-16:8
# +2: test: Const(2)
# +1: test.position: 13:6-13:7
while 2:
    pass
else:
    pass
