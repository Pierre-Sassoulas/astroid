# FunctionDef, AsyncFunctionDef, Decorators, Lambda, Arguments.
# +29: args: a: int = 0, /, var: int = 1, *args, keyword: int = 2, **kwargs
# +28: args.annotations[0]: Name(int)
# +27: args.annotations[0].position: 33:9-33:12
# +26: args.args[0]: AssignName(var)
# +25: args.args[0].position: 33:4-33:12
# +24: args.defaults[0].position: 32:13-32:14
# +23: args.defaults[1]: Const(1)
# +22: args.defaults[1].position: 33:15-33:16
# +21: args.end_lineno: 34
# +20: args.kw_defaults[0]: Const(2)
# +19: args.kw_defaults[0].position: 34:19-34:20
# +18: args.kwargannotation: Name(Any)
# +17: args.kwargannotation.position: 34:32-34:35
# +16: args.kwonlyargs[0]: AssignName(keyword)
# +15: args.kwonlyargs[0].position: 34:4-34:16
# +14: args.kwonlyargs_annotations[0]: Name(int)
# +13: args.kwonlyargs_annotations[0].position: 34:13-34:16
# +12: args.lineno: 32
# +11: args.posonlyargs[0]: AssignName(a)
# +10: args.posonlyargs[0].position: 32:4-32:10
# +9: args.posonlyargs_annotations[0]: Name(int)
# +8: args.posonlyargs_annotations[0].position: 32:7-32:10
# +7: args.varargannotation: Name(Any)
# +6: args.varargannotation.position: 33:25-33:28
# +5: body[0]: Pass(pass)
# +4: body[0].position: 36:4-36:8
# +3: position: 31:0-36:8
# +2: returns: Const(None)
# +1: returns.position: 35:5-35:9
def func(
    a: int = 0, /,
    var: int = 1, *args: Any,
    keyword: int = 2, **kwargs: Any
) -> None:
    pass

@decorator1
@decorator2
async def func():
# -1: decorators: Decorators
# -2: decorators.nodes[0]: Name(decorator1)
# -3: decorators.nodes[0].position: 38:1-38:11
# -4: decorators.nodes[1]: Name(decorator2)
# -5: decorators.nodes[1].position: 39:1-39:11
# -6: decorators.position: 38:0-39:11
# -7: position: 38:0-48:8
    pass

# +6: args: x
# +5: args.args[0]: AssignName(x)
# +4: args.args[0].position: 56:7-56:8
# +3: body: Const(2)
# +2: body.position: 56:10-56:11
# +1: position: 56:0-56:11
lambda x: 2
