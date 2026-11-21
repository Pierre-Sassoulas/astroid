# Dict, DictUnpack.
# +5: items[0][0]: Const(1)
# +4: items[0][0].position: 8:4-8:5
# +3: items[0][1]: Const('Hello')
# +2: items[0][1].position: 8:7-8:14
# +1: position: 7:0-10:1
{
    1: "Hello",
    **{2: "World"}  # position: 9:6-9:18
}
