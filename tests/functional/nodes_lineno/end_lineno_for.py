# For, AsyncFor.
# +9: body[0]: Pass(pass)
# +8: body[0].position: 12:4-12:8
# +7: iter: Name(lst)
# +6: iter.position: 11:9-11:12
# +5: orelse[0]: Pass(pass)
# +4: orelse[0].position: 14:4-14:8
# +3: position: 11:0-14:8
# +2: target: AssignName(i)
# +1: target.position: 11:4-11:5
for i in lst:
    pass
else:
    pass

# +7: body[0]: Pass(pass)
# +6: body[0].position: 24:4-24:8
# +5: iter: Name(lst)
# +4: iter.position: 23:15-23:18
# +3: position: 23:0-24:8
# +2: target: AssignName(i)
# +1: target.position: 23:10-23:11
async for i in lst:
    pass
