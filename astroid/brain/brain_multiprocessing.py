# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from astroid import nodes
from astroid.bases import BoundMethod, Instance
from astroid.brain.helpers import register_module_extender
from astroid.builder import parse
from astroid.exceptions import InferenceError
from astroid.manager import AstroidManager
from astroid.nodes.scoped_nodes import FunctionDef


def _multiprocessing_transform() -> nodes.Module:
    module = parse("""
    from multiprocessing.managers import SyncManager
    def Manager():
        return SyncManager()
    """)
    # Multiprocessing uses a getattr lookup inside contexts,
    # in order to get the attributes they need. Since it's extremely
    # dynamic, we use this approach to fake it.
    node = parse("""
    from multiprocessing.context import DefaultContext, BaseContext
    default = DefaultContext()
    base = BaseContext()
    """)
    try:
        context = next(node["default"].infer())
        base = next(node["base"].infer())
    except (InferenceError, StopIteration):
        return module

    if not isinstance(context, Instance) or not isinstance(base, Instance):
        return module

    for instance in (context, base):
        for key, values in instance.locals.items():
            if key.startswith("_"):
                continue

            value = values[0]
            if isinstance(value, FunctionDef):
                # We need to rebound this, since otherwise
                # it will have an extra argument (self).
                value = BoundMethod(value, instance)
            module[key] = value
    return module


def _multiprocessing_managers_transform() -> nodes.Module:
    return parse("""
    import array
    import threading
    import multiprocessing.pool as pool
    import queue

    class Namespace(object):
        pass

    class Value(object):
        def __init__(self, typecode, value, lock=True):
            self._typecode = typecode
            self._value = value
        def get(self):
            return self._value
        def set(self, value):
            self._value = value
        def __repr__(self):
            return '%s(%r, %r)'%(type(self).__name__, self._typecode, self._value)
        value = property(get, set)

    def Array(typecode, sequence, lock=True):
        return array.array(typecode, sequence)

    class SyncManager(object):
        Queue = JoinableQueue = queue.Queue
        Event = threading.Event
        RLock = threading.RLock
        Lock = threading.Lock
        BoundedSemaphore = threading.BoundedSemaphore
        Condition = threading.Condition
        Barrier = threading.Barrier
        Pool = pool.Pool
        list = list
        dict = dict
        Value = Value
        Array = Array
        Namespace = Namespace
        __enter__ = lambda self: self
        __exit__ = lambda *args: args

        def start(self, initializer=None, initargs=None):
            pass
        def shutdown(self):
            pass
    """)


def register(manager: AstroidManager) -> None:
    register_module_extender(
        manager, "multiprocessing.managers", _multiprocessing_managers_transform
    )
    register_module_extender(manager, "multiprocessing", _multiprocessing_transform)
