from enum import Enum
class Animal(Enum):
    a = 1
    __members__ = {}
# +2: inferred: Dict({'a': a, '__members__': __members__})
# +1: inferred.locals: __annotations__, __class__, __class_getitem__, __contains__, __delattr__, __delitem__, __dir__, __eq__, __format__, __ge__, __getattribute__, __getitem__, __getstate__, __gt__, __hash__, __init__, __init_subclass__, __ior__, __iter__, __le__, __len__, __lt__, __module__, __ne__, __new__, __or__, __qualname__, __reduce__, __reduce_ex__, __repr__, __reversed__, __ror__, __setattr__, __setitem__, __sizeof__, __str__, __subclasshook__, clear, copy, fromkeys, get, items, keys, pop, popitem, setdefault, update, values
Animal.__members__
