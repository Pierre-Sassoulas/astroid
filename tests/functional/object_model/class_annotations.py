# Test that the `__annotations__` attribute is avaiable in the class scope
class Test:
    __annotations__  # inferred: Uninferable
Test.__annotations__  # inferred: Uninferable
