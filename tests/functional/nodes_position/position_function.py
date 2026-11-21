# Position should only include keyword and name.
#
# >>> def func(var: int = 42):
# >>> ^^^^^^^^
def a():  # position: 5:0-6:7
    ...

def b():  # position: 8:0-9:19
    '''Docstring'''

def c(  # position: 11:0-15:11
    var: int = 42
):
    def d():  # position: 14:4-15:11
        ...

@decorator
def e():  # position: 17:0-19:7
    ...
