# Try, ExceptHandler.
# +13: body[0]: Pass(pass)
# +12: body[0].position: 16:4-16:8
# +11: handlers[0]: ExceptHandler
# +10: handlers[0].body[0]: Pass(pass)
# +9: handlers[0].body[0].position: 18:4-18:8
# +8: handlers[0].name: AssignName(ex)
# +7: handlers[0].name.position: 17:0-18:8
# +6: handlers[0].position: 17:0-18:8
# +5: handlers[0].type: Name(KeyError)
# +4: handlers[0].type.position: 17:7-17:15
# +3: orelse[0]: Pass(pass)
# +2: orelse[0].position: 22:4-22:8
# +1: position: 15:0-22:8
try:
    pass
except KeyError as ex:
    pass
except AttributeError as ex:
    pass
else:
    pass

# +4: body[0].position: 29:4-29:8
# +3: finalbody[0]: Pass(pass)
# +2: finalbody[0].position: 35:4-35:8
# +1: position: 28:0-35:8
try:
    pass
except KeyError as ex:
    pass
else:
    pass
finally:
    pass
