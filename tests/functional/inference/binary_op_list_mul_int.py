# Test correct handling on list multiplied by int when there are more than one.
from ctypes import c_int
# +2: inferred: List(Instance(ctypes.c_int), Instance(ctypes.c_int), Instance(ctypes.c_int), Instance(ctypes.c_int))
# +1: inferred.itered(): [Instance(ctypes.c_int), Instance(ctypes.c_int), Instance(ctypes.c_int), Instance(ctypes.c_int)]
seq = [c_int()] * 4
