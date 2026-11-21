# ClassDef, Keyword.
@decorator1
@decorator2
class X(Parent, var=42):
# -1: bases[0]: Name(Parent)
# -2: bases[0].position: 4:8-4:14
# -3: body[0]: Pass(pass)
# -4: body[0].position: 14:4-14:8
# -5: decorators: Decorators
# -6: decorators.position: 2:0-3:11
# -7: keywords[0]: Keyword(var=42)
# -8: keywords[0].position: 4:16-4:22
# -9: position: 4:0-14:8
    pass
