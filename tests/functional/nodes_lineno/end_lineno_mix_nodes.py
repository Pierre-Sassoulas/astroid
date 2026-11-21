# Await, Starred, Yield, YieldFrom.
await func  # position: 2:0-2:10  # value: Name(func)  # value.position: 2:6-2:10
*args  # position: 3:0-3:5  # value: Name(args)  # value.position: 3:1-3:5
yield 42  # position: 4:0-4:8  # value: Const(42)  # value.position: 4:6-4:8
yield from (1, 2)  # position: 5:0-5:17  # value: Tuple((1, 2))  # value.position: 5:11-5:17
