# Position should only include keyword and name.
#
# >>> class A(Parent):
# >>> ^^^^^^^
class A:  # position: 5:0-6:7
    ...

class B(A):  # position: 8:0-9:8
    pass

class C:  # position: 11:0-15:11
    '''Docstring'''

    class D:  # position: 14:4-15:11
        ...

class E:  # position: 17:0-19:11
    def f():
        ...

@decorator
class F:  # position: 22:0-23:7
    ...
