# If, IfExp, NamedExpr.
# +7: body[0]: Pass(pass)
# +6: body[0].position: 17:4-17:8
# +5: orelse[0]: Pass(pass)
# +4: orelse[0].position: 19:4-19:8
# +3: position: 9:0-19:8
# +2: test: NamedExpr((var := 2))
# +1: test.position: 15:4-15:12
if (
    # +5: position: 15:4-15:12
    # +4: target: AssignName(var)
    # +3: target.position: 15:4-15:7
    # +2: value: Const(2)
    # +1: value.position: 15:11-15:12
    var := 2
):
    pass
else:
    pass

# +7: body: Const(2)
# +6: body.position: 28:0-28:1
# +5: orelse: Const(1)
# +4: orelse.position: 28:15-28:16
# +3: position: 28:0-28:16
# +2: test: Const(True)
# +1: test.position: 28:5-28:9
2 if True else 1
