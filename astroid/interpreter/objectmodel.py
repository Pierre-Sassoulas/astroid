# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""
Data object model, as per https://docs.python.org/3/reference/datamodel.html.

This module describes, at least partially, a data object model for some
of astroid's nodes. The model contains special attributes that nodes such
as functions, classes, modules etc have, such as __doc__, __class__,
__module__ etc, being used when doing attribute lookups over nodes.

For instance, inferring `obj.__class__` will first trigger an inference
of the `obj` variable. If it was successfully inferred, then an attribute
`__class__ will be looked for in the inferred object. This is the part
where the data model occurs. The model is attached to those nodes
and the lookup mechanism will try to see if attributes such as
`__class__` are defined by the model or not. If they are defined,
the model will be requested to return the corresponding value of that
attribute. Thus the model can be viewed as a special part of the lookup
mechanism.
"""

from __future__ import annotations

import itertools
import os
import types
from collections.abc import Iterator
from functools import lru_cache
from typing import TYPE_CHECKING, Generic, Literal, Self, TypeVar, cast

from astroid import bases, nodes, util
from astroid.context import InferenceContext, copy_context
from astroid.exceptions import AttributeInferenceError, InferenceError, NoDefault
from astroid.manager import AstroidManager
from astroid.nodes import node_classes
from astroid.typing import InferenceResult, SuccessfulInferenceResult

if TYPE_CHECKING:
    from astroid import objects
    from astroid.objects import Property

IMPL_PREFIX = "attr_"
LEN_OF_IMPL_PREFIX = len(IMPL_PREFIX)

_InstanceT_co = TypeVar(
    "_InstanceT_co", bound=SuccessfulInferenceResult, covariant=True
)
_FunctionT_co = TypeVar(
    "_FunctionT_co",
    bound="nodes.FunctionDef | nodes.Lambda | bases.UnboundMethod | bases.Generator",
    covariant=True,
)


def _dunder_dict(
    instance: nodes.Module | bases.Instance,
    attributes: dict[str, list[InferenceResult]],
) -> node_classes.Dict:
    obj = node_classes.Dict(
        parent=instance,
        lineno=instance.lineno,
        col_offset=instance.col_offset,
        end_lineno=instance.end_lineno,
        end_col_offset=instance.end_col_offset,
    )

    # Convert the keys to node strings
    keys = [
        node_classes.Const(value=value, parent=obj) for value in list(attributes.keys())
    ]

    # The original attribute has a list of elements for each key,
    # but that is not useful for retrieving the special attribute's value.
    # In this case, we're picking the last value from each list.
    values = [elem[-1] for elem in attributes.values()]

    items: list[tuple[InferenceResult, InferenceResult]] = list(zip(keys, values))
    obj.postinit(items)
    return obj


def _get_bound_node(
    model: ObjectModel[SuccessfulInferenceResult],
) -> SuccessfulInferenceResult:
    # Proxies, but also some nodes such as Const or Super, expose the class they
    # stand for as ``_proxied``: they have no common base class to check against.
    instance = model._instance
    bound: SuccessfulInferenceResult = getattr(instance, "_proxied", instance)
    return bound


def _builtins_class(name: str) -> nodes.ClassDef:
    builtins_class = AstroidManager().builtins_module[name]
    assert isinstance(builtins_class, nodes.ClassDef)
    return builtins_class


class ObjectModel(Generic[_InstanceT_co]):
    """Special attributes of the nodes or proxies of type ``_InstanceT_co``."""

    def __init__(self) -> None:
        self._bound_instance: _InstanceT_co | None = None

    def __repr__(self) -> str:
        import pprint  # pylint: disable=import-outside-toplevel

        result: list[str] = []
        cname = type(self).__name__
        string = "%(cname)s(%(fields)s)"
        alignment = len(cname) + 1
        for field in sorted(self.attributes()):
            width = max(80 - len(field) - alignment, 1)
            try:
                lines = pprint.pformat(field, indent=2, width=width).splitlines(True)
            except ValueError:
                lines = [f"<{type(field).__name__}>"]

            inner = [lines[0]]
            for line in lines[1:]:
                inner.append(" " * alignment + line)
            result.append(field)

        return string % {
            "cname": cname,
            "fields": (",\n" + " " * alignment).join(result),
        }

    @property
    def _instance(self) -> _InstanceT_co:
        """The node or proxy that ``__call__`` or ``__get__`` bound the model to."""
        assert self._bound_instance is not None, "The model is not bound to a node"
        return self._bound_instance

    def __call__(self, instance: SuccessfulInferenceResult | None) -> Self:
        # A model is bound to the instances of the classes that declare it as
        # their ``special_attributes``: those are of type ``_InstanceT_co``.
        self._bound_instance = cast("_InstanceT_co | None", instance)
        return self

    def __get__(
        self, instance: SuccessfulInferenceResult | None, cls: type | None = None
    ) -> Self:
        # ObjectModel needs to be a descriptor so that just doing
        # `special_attributes = SomeObjectModel` should be enough in the body of a node.
        # But at the same time, node.special_attributes should return an object
        # which can be used for manipulating the special attributes. That's the reason
        # we pass the instance through which it got accessed to ObjectModel.__call__,
        # returning itself afterwards, so we can still have access to the
        # underlying data model and to the instance for which it got accessed.
        return self.__call__(instance)

    def __contains__(self, name: str) -> bool:
        return name in self.attributes()

    @lru_cache  # noqa
    def attributes(self) -> list[str]:
        """Get the attributes which are exported by this object model."""
        return [o[LEN_OF_IMPL_PREFIX:] for o in dir(self) if o.startswith(IMPL_PREFIX)]

    def lookup(self, name: str) -> InferenceResult:
        """Look up the given *name* in the current model.

        It should return an AST or an interpreter object,
        but if the name is not found, then an AttributeInferenceError will be raised.
        """
        if name in self.attributes():
            attribute: InferenceResult = getattr(self, IMPL_PREFIX + name)
            return attribute
        raise AttributeInferenceError(target=self._instance, attribute=name)

    @property
    def attr___new__(self) -> bases.BoundMethod:
        """Calling cls.__new__(type) on an object returns an instance of 'type'."""
        from astroid import builder  # pylint: disable=import-outside-toplevel

        # ``__new__`` is a static method: the class is passed explicitly and
        # ``BoundMethod.implicit_parameters()`` is 0 for it, so the first
        # parameter is the one filled by ``cls`` in ``self.__new__(cls)`` or
        # ``super().__new__(cls)``. The *args and **kwargs are necessary not
        # to trigger warnings about extra parameters for ``__new__`` methods
        # we don't infer correctly (e.g. ``tp_new`` of C types), just like
        # the ``__init__`` fallback below.
        node = builder._extract_single_node(
            """def __new__(cls, *args, **kwargs): return cls()"""
        )
        assert isinstance(node, nodes.FunctionDef)
        # We set the parent as being the ClassDef of 'object' as that
        # triggers correct inference as a call to __new__ in bases.py
        node.parent = _builtins_class("object")

        return bases.BoundMethod(proxy=node, bound=_get_bound_node(self))

    @property
    def attr___init__(self) -> bases.BoundMethod:
        """Calling cls.__init__() normally returns None."""
        from astroid import builder  # pylint: disable=import-outside-toplevel

        # The *args and **kwargs are necessary not to trigger warnings about missing
        # or extra parameters for '__init__' methods we don't infer correctly.
        # This BoundMethod is the fallback value for those.
        node = builder._extract_single_node(
            """def __init__(self, *args, **kwargs): return None"""
        )
        assert isinstance(node, nodes.FunctionDef)
        # We set the parent as being the ClassDef of 'object' as that
        # is where this method originally comes from
        node.parent = _builtins_class("object")

        return bases.BoundMethod(proxy=node, bound=_get_bound_node(self))

    # Base object attributes that return Unknown as fallback placeholders.
    @property
    def attr___ne__(self) -> InferenceResult:
        return node_classes.Unknown(parent=self._instance)

    attr___class__ = attr___ne__
    attr___delattr__ = attr___ne__
    attr___dir__ = attr___ne__
    attr___doc__ = attr___ne__
    attr___eq__ = attr___ne__
    attr___format__ = attr___ne__
    attr___ge__ = attr___ne__
    attr___getattribute__ = attr___ne__
    attr___getstate__ = attr___ne__
    attr___gt__ = attr___ne__
    attr___hash__ = attr___ne__
    attr___init_subclass__ = attr___ne__
    attr___le__ = attr___ne__
    attr___lt__ = attr___ne__
    attr___reduce__ = attr___ne__
    attr___reduce_ex__ = attr___ne__
    attr___repr__ = attr___ne__
    attr___setattr__ = attr___ne__
    attr___sizeof__ = attr___ne__
    attr___str__ = attr___ne__
    attr___subclasshook__ = attr___ne__


class ModuleModel(ObjectModel["nodes.Module"]):
    def _builtins(self) -> InferenceResult:
        builtins_ast_module = AstroidManager().builtins_module
        return builtins_ast_module.special_attributes.lookup("__dict__")

    @property
    def attr_builtins(self) -> InferenceResult:
        return self._builtins()

    @property
    def attr___path__(self) -> node_classes.List:
        if not self._instance.package:
            raise AttributeInferenceError(target=self._instance, attribute="__path__")

        # A package always has a path.
        package_path = self._instance.path
        assert package_path is not None
        path_objs: list[InferenceResult] = [
            node_classes.Const(
                value=(
                    path if not path.endswith("__init__.py") else os.path.dirname(path)
                ),
                parent=self._instance,
            )
            for path in package_path
        ]

        container = node_classes.List(parent=self._instance)
        container.postinit(path_objs)

        return container

    @property
    def attr___name__(self) -> node_classes.Const:
        return node_classes.Const(value=self._instance.name, parent=self._instance)

    @property
    def attr___doc__(self) -> node_classes.Const:
        return node_classes.Const(
            value=getattr(self._instance.doc_node, "value", None),
            parent=self._instance,
        )

    @property
    def attr___file__(self) -> node_classes.Const:
        return node_classes.Const(value=self._instance.file, parent=self._instance)

    @property
    def attr___dict__(self) -> node_classes.Dict:
        return _dunder_dict(self._instance, self._instance.globals)

    @property
    def attr___package__(self) -> node_classes.Const:
        if not self._instance.package:
            value = ""
        else:
            value = self._instance.name

        return node_classes.Const(value=value, parent=self._instance)

    # These are related to the Python 3 implementation of the
    # import system,
    # https://docs.python.org/3/reference/import.html#import-related-module-attributes

    @property
    def attr___spec__(self) -> node_classes.Unknown:
        # No handling for now.
        return node_classes.Unknown(parent=self._instance)

    @property
    def attr___loader__(self) -> node_classes.Unknown:
        # No handling for now.
        return node_classes.Unknown(parent=self._instance)

    @property
    def attr___cached__(self) -> node_classes.Unknown:
        # No handling for now.
        return node_classes.Unknown(parent=self._instance)


class BaseFunctionModel(ObjectModel[_FunctionT_co]):
    """Special attributes shared by functions, methods and generators."""

    def _is_builtin_func(self) -> bool:
        func = self._instance
        return isinstance(func.parent, nodes.Module) and not func.root().pure_python

    @property
    def attr___name__(self) -> node_classes.Const:
        return node_classes.Const(value=self._instance.name, parent=self._instance)

    @property
    def attr___doc__(self) -> node_classes.Const:
        func = self._instance
        # A lambda has no docstring.
        doc_node = None if isinstance(func, nodes.Lambda) else func.doc_node
        return node_classes.Const(
            value=getattr(doc_node, "value", None),
            parent=func,
        )

    @property
    def attr___qualname__(self) -> node_classes.Const:
        return node_classes.Const(value=self._instance.qname(), parent=self._instance)

    @property
    def attr___defaults__(self) -> node_classes.Const | node_classes.Tuple:
        func = self._instance
        if self._is_builtin_func():
            raise AttributeInferenceError(target=func, attribute="__defaults__")
        if not func.args.defaults:
            return node_classes.Const(value=None, parent=func)

        defaults_obj = node_classes.Tuple(parent=func)
        defaults_obj.postinit(func.args.defaults)
        return defaults_obj

    @property
    def attr___annotations__(self) -> node_classes.Dict:
        if self._is_builtin_func():
            raise AttributeInferenceError(
                target=self._instance, attribute="__annotations__"
            )
        obj = node_classes.Dict(
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )

        # A lambda cannot annotate its return.
        if isinstance(self._instance, nodes.Lambda) or not self._instance.returns:
            returns = None
        else:
            returns = self._instance.returns

        args = self._instance.args
        pair_annotations = itertools.chain(
            zip(args.args or [], args.annotations),
            zip(args.kwonlyargs, args.kwonlyargs_annotations),
            zip(args.posonlyargs or [], args.posonlyargs_annotations),
        )

        annotations: dict[str, nodes.NodeNG] = {
            arg.name: annotation for (arg, annotation) in pair_annotations if annotation
        }
        # Only a named *args or **kwargs can be annotated.
        if args.varargannotation:
            assert args.vararg is not None
            annotations[args.vararg] = args.varargannotation
        if args.kwargannotation:
            assert args.kwarg is not None
            annotations[args.kwarg] = args.kwargannotation
        if returns:
            annotations["return"] = returns

        items: list[tuple[InferenceResult, InferenceResult]] = [
            (node_classes.Const(key, parent=obj), value)
            for (key, value) in annotations.items()
        ]

        obj.postinit(items)
        return obj

    @property
    def attr___dict__(self) -> node_classes.Dict:
        if self._is_builtin_func():
            raise AttributeInferenceError(target=self._instance, attribute="__dict__")
        return node_classes.Dict(
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )

    @property
    def attr___globals__(self) -> node_classes.Dict:
        if self._is_builtin_func():
            raise AttributeInferenceError(
                target=self._instance, attribute="__globals__"
            )
        return node_classes.Dict(
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )

    @property
    def attr___kwdefaults__(self) -> node_classes.Dict:
        if self._is_builtin_func():
            raise AttributeInferenceError(
                target=self._instance, attribute="__kwdefaults__"
            )

        def _default_args(
            args: nodes.Arguments, parent: node_classes.Dict
        ) -> Iterator[tuple[node_classes.Const, InferenceResult]]:
            for arg in args.kwonlyargs:
                try:
                    default = args.default_value(arg.name)
                except NoDefault:
                    continue

                name = node_classes.Const(arg.name, parent=parent)
                yield name, default

        args = self._instance.args
        obj = node_classes.Dict(
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )
        defaults = dict(_default_args(args, obj))

        items: list[tuple[InferenceResult, InferenceResult]] = list(defaults.items())
        obj.postinit(items)
        return obj

    @property
    def attr___module__(self) -> node_classes.Const:
        return node_classes.Const(self._instance.root().qname())

    @property
    def attr___get__(self) -> bases.BoundMethod:
        func = self._instance

        if self._is_builtin_func():
            raise AttributeInferenceError(target=func, attribute="__get__")

        class DescriptorBoundMethod(bases.BoundMethod):
            """Bound method which knows how to understand calling descriptor
            binding.
            """

            def implicit_parameters(self) -> Literal[0]:
                # Different than BoundMethod since the signature
                # is different.
                return 0

            def infer_call_result(
                self,
                caller: SuccessfulInferenceResult | None,
                context: InferenceContext | None = None,
            ) -> Iterator[bases.BoundMethod]:
                if len(caller.args) > 2 or len(caller.args) < 1:
                    raise InferenceError(
                        "Invalid arguments for descriptor binding",
                        target=self,
                        context=context,
                    )

                context = copy_context(context)
                try:
                    cls = next(caller.args[0].infer(context=context))
                except StopIteration as e:
                    raise InferenceError(context=context, node=caller.args[0]) from e

                if isinstance(cls, util.UninferableBase):
                    raise InferenceError(
                        "Invalid class inferred", target=self, context=context
                    )

                # The `func` can already be an Unbound or BoundMethod (a subclass of
                # UnboundMethod): wrap it as a BoundMethod like we do below when
                # constructing the function from scratch.
                if isinstance(func, bases.UnboundMethod):
                    yield bases.BoundMethod(proxy=func, bound=cls)
                    return

                # Rebuild the original value, but with the parent set as the
                # class where it will be bound.
                new_func_kwargs = {
                    "name": func.name,
                    "lineno": func.lineno,
                    "col_offset": func.col_offset,
                    "parent": func.parent,
                    "end_lineno": func.end_lineno,
                    "end_col_offset": func.end_col_offset,
                }
                # pylint: disable-next=import-outside-toplevel; circular import
                from astroid import objects

                if isinstance(func, objects.PartialFunction):
                    new_func_kwargs["filled_args"] = func.filled_args
                    new_func_kwargs["filled_keywords"] = func.filled_keywords

                new_func = func.__class__(**new_func_kwargs)
                # pylint: disable=no-member
                new_func.postinit(
                    func.args,
                    func.body,
                    func.decorators,
                    func.returns,
                    doc_node=func.doc_node,
                )

                # Build a proper bound method that points to our newly built function.
                proxy = bases.UnboundMethod(new_func)
                yield bases.BoundMethod(proxy=proxy, bound=cls)

            @property
            def args(self) -> nodes.Arguments:
                """Overwrite the underlying args to match those of the underlying func.

                Usually the underlying *func* is a function/method, as in:

                    def test(self):
                        pass

                This has only the *self* parameter but when we access test.__get__
                we get a new object which has two parameters, *self* and *type*.
                """
                nonlocal func
                arguments = nodes.Arguments(
                    parent=func.args.parent, vararg=None, kwarg=None
                )

                positional_or_keyword_params = func.args.args.copy()
                positional_or_keyword_params.append(
                    nodes.AssignName(
                        name="type",
                        lineno=0,
                        col_offset=0,
                        parent=arguments,
                        end_lineno=None,
                        end_col_offset=None,
                    )
                )

                positional_only_params = func.args.posonlyargs.copy()

                arguments.postinit(
                    args=positional_or_keyword_params,
                    posonlyargs=positional_only_params,
                    defaults=[],
                    kwonlyargs=[],
                    kw_defaults=[],
                    annotations=[],
                    kwonlyargs_annotations=[],
                    posonlyargs_annotations=[],
                )
                return arguments

        return DescriptorBoundMethod(proxy=self._instance, bound=self._instance)

    # Function-specific attributes.
    @property
    def attr___call__(self) -> node_classes.Unknown:
        return node_classes.Unknown(parent=self._instance)

    attr___builtins__ = attr___call__
    attr___closure__ = attr___call__
    attr___code__ = attr___call__
    attr___type_params__ = attr___call__


class FunctionModel(BaseFunctionModel["nodes.FunctionDef | nodes.Lambda"]):
    """Special attributes of functions and lambdas."""


class ClassModel(ObjectModel["nodes.ClassDef"]):
    def __init__(self) -> None:
        # Add a context so that inferences called from an instance don't recurse endlessly
        self.context = InferenceContext()

        super().__init__()

    @property
    def attr___annotations__(self) -> node_classes.Unknown:
        return node_classes.Unknown(parent=self._instance)

    @property
    def attr___module__(self) -> node_classes.Const:
        return node_classes.Const(self._instance.root().qname())

    @property
    def attr___name__(self) -> node_classes.Const:
        return node_classes.Const(self._instance.name)

    @property
    def attr___qualname__(self) -> node_classes.Const:
        return node_classes.Const(self._instance.qname())

    @property
    def attr___doc__(self) -> node_classes.Const:
        return node_classes.Const(getattr(self._instance.doc_node, "value", None))

    @property
    def attr___mro__(self) -> node_classes.Tuple:
        mro: list[InferenceResult] = list(self._instance.mro())
        obj = node_classes.Tuple(parent=self._instance)
        obj.postinit(mro)
        return obj

    @property
    def attr_mro(self) -> bases.BoundMethod:
        other_self = self

        # Cls.mro is a method and we need to return one in order to have a proper inference.
        # The method we're returning is capable of inferring the underlying MRO though.
        class MroBoundMethod(bases.BoundMethod):
            def infer_call_result(
                self,
                caller: SuccessfulInferenceResult | None,
                context: InferenceContext | None = None,
            ) -> Iterator[node_classes.Tuple]:
                yield other_self.attr___mro__

        implicit_metaclass = self._instance.implicit_metaclass()
        # The implicit metaclass is ``builtins.type``, which defines the method.
        assert isinstance(implicit_metaclass, nodes.ClassDef)
        mro_method = implicit_metaclass.locals["mro"][0]
        assert isinstance(mro_method, nodes.FunctionDef)
        return MroBoundMethod(proxy=mro_method, bound=implicit_metaclass)

    @property
    def attr___bases__(self) -> node_classes.Tuple:
        obj = node_classes.Tuple(parent=self._instance)
        context = InferenceContext()
        elts: list[InferenceResult] = list(self._instance._inferred_bases(context))
        obj.postinit(elts=elts)
        return obj

    @property
    def attr___class__(self) -> InferenceResult:
        # pylint: disable=import-outside-toplevel; circular import
        from astroid import helpers

        return helpers.object_type(self._instance)

    @property
    def attr___subclasses__(self) -> bases.BoundMethod:
        """Get the subclasses of the underlying class.

        This looks only in the current module for retrieving the subclasses,
        thus it might miss a couple of them.
        """

        qname = self._instance.qname()
        root = self._instance.root()
        classes: list[InferenceResult] = [
            cls
            for cls in root.nodes_of_class(nodes.ClassDef)
            if cls != self._instance and cls.is_subtype_of(qname, context=self.context)
        ]

        obj = node_classes.List(parent=self._instance)
        obj.postinit(classes)

        class SubclassesBoundMethod(bases.BoundMethod):
            def infer_call_result(
                self,
                caller: SuccessfulInferenceResult | None,
                context: InferenceContext | None = None,
            ) -> Iterator[node_classes.List]:
                yield obj

        implicit_metaclass = self._instance.implicit_metaclass()
        # The implicit metaclass is ``builtins.type``, which defines the method.
        assert isinstance(implicit_metaclass, nodes.ClassDef)
        subclasses_method = implicit_metaclass.locals["__subclasses__"][0]
        assert isinstance(subclasses_method, nodes.FunctionDef)
        return SubclassesBoundMethod(proxy=subclasses_method, bound=implicit_metaclass)

    @property
    def attr___dict__(self) -> node_classes.Dict:
        return node_classes.Dict(
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )

    @property
    def attr___call__(self) -> bases.Instance:
        """Calling a class A() returns an instance of A."""
        return self._instance.instantiate_class()


class SuperModel(ObjectModel["objects.Super"]):
    @property
    def attr___thisclass__(self) -> SuccessfulInferenceResult:
        return self._instance.mro_pointer

    @property
    def attr___self_class__(self) -> nodes.ClassDef | None:
        return self._instance._self_class

    @property
    def attr___self__(self) -> SuccessfulInferenceResult:
        return self._instance.type

    @property
    def attr___class__(self) -> InferenceResult:
        proxied: InferenceResult = self._instance._proxied
        return proxied


class UnboundMethodModel(BaseFunctionModel["bases.UnboundMethod"]):
    @property
    def attr___class__(self) -> InferenceResult:
        # pylint: disable=import-outside-toplevel; circular import
        from astroid import helpers

        return helpers.object_type(self._instance)

    @property
    def attr___func__(self) -> nodes.FunctionDef | bases.UnboundMethod:
        return self._instance._proxied

    @property
    def attr___self__(self) -> node_classes.Const:
        return node_classes.Const(value=None, parent=self._instance)

    attr_im_func = attr___func__
    attr_im_class = attr___class__
    attr_im_self = attr___self__


class ContextManagerModel(ObjectModel[_InstanceT_co]):
    """Model for context managers.

    Based on 3.3.9 of the Data Model documentation:
    https://docs.python.org/3/reference/datamodel.html#with-statement-context-managers
    """

    @property
    def attr___enter__(self) -> bases.BoundMethod:
        """Representation of the base implementation of __enter__.

        As per Python documentation:
        Enter the runtime context related to this object. The with statement
        will bind this method's return value to the target(s) specified in the
        as clause of the statement, if any.
        """
        from astroid import builder  # pylint: disable=import-outside-toplevel

        node = builder._extract_single_node("""def __enter__(self): ...""")
        assert isinstance(node, nodes.FunctionDef)
        # We set the parent as being the ClassDef of 'object' as that
        # is where this method originally comes from
        node.parent = _builtins_class("object")

        return bases.BoundMethod(proxy=node, bound=_get_bound_node(self))

    @property
    def attr___exit__(self) -> bases.BoundMethod:
        """Representation of the base implementation of __exit__.

        As per Python documentation:
        Exit the runtime context related to this object. The parameters describe the
        exception that caused the context to be exited. If the context was exited
        without an exception, all three arguments will be None.
        """
        from astroid import builder  # pylint: disable=import-outside-toplevel

        node = builder._extract_single_node(
            """def __exit__(self, exc_type, exc_value, traceback): ..."""
        )
        assert isinstance(node, nodes.FunctionDef)
        # We set the parent as being the ClassDef of 'object' as that
        # is where this method originally comes from
        node.parent = _builtins_class("object")

        return bases.BoundMethod(proxy=node, bound=_get_bound_node(self))


class BoundMethodModel(BaseFunctionModel["bases.BoundMethod"]):
    @property
    def attr___func__(self) -> nodes.FunctionDef | nodes.Lambda:
        # Proxy depth varies: an instance method accessed through an instance
        # proxies another method proxy, a classmethod on its class or a lambda
        # class attribute proxies the function directly.
        proxied = self._instance._proxied
        while isinstance(proxied, bases.UnboundMethod):
            proxied = proxied._proxied
        return proxied

    @property
    def attr___self__(self) -> SuccessfulInferenceResult | None:
        return self._instance.bound


class GeneratorBaseModel(
    BaseFunctionModel["bases.Generator"], ContextManagerModel["bases.Generator"]
):
    def __init__(self, gen_class: nodes.ClassDef) -> None:
        super().__init__()
        for name, values in gen_class.locals.items():
            method = values[0]
            if isinstance(method, nodes.FunctionDef):
                # The model is not bound to a generator yet: these methods
                # have no bound node.
                method = bases.BoundMethod(method, None)

            def patched(
                cls: GeneratorBaseModel, meth: InferenceResult = method
            ) -> InferenceResult:
                return meth

            setattr(type(self), IMPL_PREFIX + name, property(patched))

    @property
    def attr___name__(self) -> node_classes.Const:
        return node_classes.Const(
            value=self._instance.parent.name, parent=self._instance
        )

    @property
    def attr___doc__(self) -> node_classes.Const:
        return node_classes.Const(
            value=getattr(self._instance.parent.doc_node, "value", None),
            parent=self._instance,
        )


class GeneratorModel(GeneratorBaseModel):
    def __init__(self) -> None:
        super().__init__(_builtins_class("generator"))


class AsyncGeneratorModel(GeneratorBaseModel):
    def __init__(self) -> None:
        super().__init__(_builtins_class("async_generator"))


class InstanceModel(ObjectModel["bases.Instance"]):
    @property
    def attr___class__(self) -> InferenceResult:
        return self._instance._proxied

    @property
    def attr___module__(self) -> node_classes.Const:
        return node_classes.Const(self._instance.root().qname())

    @property
    def attr___doc__(self) -> node_classes.Const:
        return node_classes.Const(getattr(self._instance.doc_node, "value", None))

    @property
    def attr___dict__(self) -> node_classes.Dict:
        return _dunder_dict(self._instance, self._instance.instance_attrs)


# Exception instances


class ExceptionInstanceModel(InstanceModel):
    @property
    def attr_args(self) -> bases.Instance:
        # The arguments an exception was created with are not known from the
        # instance alone, so ``args`` is a tuple of unknown contents rather
        # than a known empty tuple.
        return _builtins_class("tuple").instantiate_class()

    @property
    def attr___traceback__(self) -> bases.Instance:
        traceback_type = _builtins_class(types.TracebackType.__name__)
        return traceback_type.instantiate_class()


class SyntaxErrorInstanceModel(ExceptionInstanceModel):
    @property
    def attr_text(self) -> node_classes.Const:
        return node_classes.Const("")


class GroupExceptionInstanceModel(ExceptionInstanceModel):
    @property
    def attr_exceptions(self) -> nodes.Tuple:
        return node_classes.Tuple(parent=self._instance)


class OSErrorInstanceModel(ExceptionInstanceModel):
    @property
    def attr_filename(self) -> node_classes.Const:
        return node_classes.Const("")

    @property
    def attr_errno(self) -> node_classes.Const:
        return node_classes.Const(0)

    @property
    def attr_strerror(self) -> node_classes.Const:
        return node_classes.Const("")

    attr_filename2 = attr_filename


class ImportErrorInstanceModel(ExceptionInstanceModel):
    @property
    def attr_name(self) -> node_classes.Const:
        return node_classes.Const("")

    @property
    def attr_path(self) -> node_classes.Const:
        return node_classes.Const("")


class UnicodeDecodeErrorInstanceModel(ExceptionInstanceModel):
    @property
    def attr_object(self) -> node_classes.Const:
        return node_classes.Const(b"")


BUILTIN_EXCEPTIONS = {
    "builtins.SyntaxError": SyntaxErrorInstanceModel,
    "builtins.ExceptionGroup": GroupExceptionInstanceModel,
    "builtins.ImportError": ImportErrorInstanceModel,
    "builtins.UnicodeDecodeError": UnicodeDecodeErrorInstanceModel,
    # These are all similar to OSError in terms of attributes
    "builtins.OSError": OSErrorInstanceModel,
    "builtins.BlockingIOError": OSErrorInstanceModel,
    "builtins.BrokenPipeError": OSErrorInstanceModel,
    "builtins.ChildProcessError": OSErrorInstanceModel,
    "builtins.ConnectionAbortedError": OSErrorInstanceModel,
    "builtins.ConnectionError": OSErrorInstanceModel,
    "builtins.ConnectionRefusedError": OSErrorInstanceModel,
    "builtins.ConnectionResetError": OSErrorInstanceModel,
    "builtins.FileExistsError": OSErrorInstanceModel,
    "builtins.FileNotFoundError": OSErrorInstanceModel,
    "builtins.InterruptedError": OSErrorInstanceModel,
    "builtins.IsADirectoryError": OSErrorInstanceModel,
    "builtins.NotADirectoryError": OSErrorInstanceModel,
    "builtins.PermissionError": OSErrorInstanceModel,
    "builtins.ProcessLookupError": OSErrorInstanceModel,
    "builtins.TimeoutError": OSErrorInstanceModel,
}


class DictModel(ObjectModel["nodes.Dict"]):
    @property
    def attr___class__(self) -> InferenceResult:
        return self._instance._proxied

    def _generic_dict_attribute(
        self, obj: objects.DictItems | objects.DictKeys | objects.DictValues, name: str
    ) -> bases.BoundMethod:
        """Generate a bound method that can infer the given *obj*."""

        class DictMethodBoundMethod(bases.BoundMethod):
            def infer_call_result(
                self,
                caller: SuccessfulInferenceResult | None,
                context: InferenceContext | None = None,
            ) -> Iterator[InferenceResult]:
                yield obj

        meth = next(self._instance._proxied.igetattr(name), None)
        # The methods of ``builtins.dict`` are found as unbound methods.
        assert isinstance(meth, bases.UnboundMethod)
        return DictMethodBoundMethod(proxy=meth, bound=self._instance)

    @property
    def attr_items(self) -> bases.BoundMethod:
        from astroid import objects  # pylint: disable=import-outside-toplevel

        elems: list[InferenceResult] = []
        obj = node_classes.List(parent=self._instance)
        for key, value in self._instance.items:
            elem = node_classes.Tuple(parent=obj)
            elem.postinit((key, value))
            elems.append(elem)
        obj.postinit(elts=elems)

        items_obj = objects.DictItems(obj)
        return self._generic_dict_attribute(items_obj, "items")

    @property
    def attr_keys(self) -> bases.BoundMethod:
        from astroid import objects  # pylint: disable=import-outside-toplevel

        keys = [key for (key, _) in self._instance.items]
        obj = node_classes.List(parent=self._instance)
        obj.postinit(elts=keys)

        keys_obj = objects.DictKeys(obj)
        return self._generic_dict_attribute(keys_obj, "keys")

    @property
    def attr_values(self) -> bases.BoundMethod:
        from astroid import objects  # pylint: disable=import-outside-toplevel

        values = [value for (_, value) in self._instance.items]
        obj = node_classes.List(parent=self._instance)
        obj.postinit(values)

        values_obj = objects.DictValues(obj)
        return self._generic_dict_attribute(values_obj, "values")


class PropertyModel(ObjectModel["Property"]):
    """Model for a builtin property."""

    def _init_function(self, name: str) -> nodes.FunctionDef:
        function = nodes.FunctionDef(
            name=name,
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )

        args = nodes.Arguments(parent=function, vararg=None, kwarg=None)
        args.postinit(
            args=[],
            defaults=[],
            kwonlyargs=[],
            kw_defaults=[],
            annotations=[],
            posonlyargs=[],
            posonlyargs_annotations=[],
            kwonlyargs_annotations=[],
        )

        function.postinit(args=args, body=[])
        return function

    @property
    def attr_fget(self) -> nodes.FunctionDef:
        func = self._instance

        class PropertyFuncAccessor(nodes.FunctionDef):
            def infer_call_result(
                self,
                caller: SuccessfulInferenceResult | None,
                context: InferenceContext | None = None,
            ) -> Iterator[InferenceResult]:
                nonlocal func
                if caller and len(caller.args) != 1:
                    raise InferenceError(
                        "fget() needs a single argument", target=self, context=context
                    )

                yield from func.function.infer_call_result(
                    caller=caller, context=context
                )

        property_accessor = PropertyFuncAccessor(
            name="fget",
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )
        property_accessor.postinit(args=func.args, body=func.body)
        return property_accessor

    @property
    def attr_fset(self) -> nodes.FunctionDef:
        func = self._instance

        def find_setter(func: Property) -> nodes.FunctionDef | None:
            """
            Given a property, find the corresponding setter function and returns it.

            :param func: property for which the setter has to be found
            :return: the setter function or None
            """
            for node in func.parent.body:
                if isinstance(node, (nodes.FunctionDef, nodes.AsyncFunctionDef)):
                    for dec_name in node.decoratornames():
                        if dec_name.endswith(func.function.name + ".setter"):
                            return node
            return None

        func_setter = find_setter(func)
        if not func_setter:
            raise InferenceError(
                f"Unable to find the setter of property {func.function.name}"
            )

        class PropertyFuncAccessor(nodes.FunctionDef):
            def infer_call_result(
                self,
                caller: SuccessfulInferenceResult | None,
                context: InferenceContext | None = None,
            ) -> Iterator[InferenceResult]:
                if caller and len(caller.args) != 2:
                    raise InferenceError(
                        "fset() needs two arguments", target=self, context=context
                    )
                yield from func_setter.infer_call_result(caller=caller, context=context)

        property_accessor = PropertyFuncAccessor(
            name="fset",
            parent=self._instance,
            lineno=self._instance.lineno,
            col_offset=self._instance.col_offset,
            end_lineno=self._instance.end_lineno,
            end_col_offset=self._instance.end_col_offset,
        )
        property_accessor.postinit(args=func_setter.args, body=func_setter.body)
        return property_accessor

    @property
    def attr_setter(self) -> nodes.FunctionDef:
        return self._init_function("setter")

    @property
    def attr_deleter(self) -> nodes.FunctionDef:
        return self._init_function("deleter")

    @property
    def attr_getter(self) -> nodes.FunctionDef:
        return self._init_function("getter")

    # pylint: enable=import-outside-toplevel
