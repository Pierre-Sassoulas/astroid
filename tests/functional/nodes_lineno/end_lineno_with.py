# With, AsyncWith.
with open(file) as fp, \
        open(file2) as fp2:
        # -1: parent: With
        # -2: parent.body[0]: Pass(pass)
        # -3: parent.body[0].position: 16:4-16:8
        # -4: parent.items[0][0]: Call(open(file))
        # -5: parent.items[0][0].position: 2:5-2:15
        # -6: parent.items[0][1]: AssignName(fp)
        # -7: parent.items[0][1].position: 2:19-2:21
        # -8: parent.items[1][0]: Call(open(file2))
        # -9: parent.items[1][0].position: 3:8-3:19
        # -10: parent.items[1][1]: AssignName(fp2)
        # -11: parent.items[1][1].position: 3:23-3:26
        # -12: parent.position: 2:0-16:8
    pass

async with open(file) as fp:
# -1: body[0]: Pass(pass)
# -2: body[0].position: 26:4-26:8
# -3: items[0][0]: Call(open(file))
# -4: items[0][0].position: 18:11-18:21
# -5: items[0][1]: AssignName(fp)
# -6: items[0][1].position: 18:25-18:27
# -7: position: 18:0-26:8
    pass
