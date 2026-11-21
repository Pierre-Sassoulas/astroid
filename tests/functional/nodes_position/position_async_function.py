# Position should only include keyword and name.
#
# >>> async def func(var: int = 42):
# >>> ^^^^^^^^^^^^^^
async def a():  # position: 5:0-6:7
    ...

async def b():  # position: 8:0-9:19
    '''Docstring'''

async def c(  # position: 11:0-15:11
    var: int = 42
):
    async def d():  # position: 14:4-15:11
        ...

@decorator
async def e():  # position: 17:0-19:7
    ...
