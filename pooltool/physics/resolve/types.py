from typing import ForwardRef, Mapping, Union

from pooltool.serialize import conversion
from pooltool.serialize.serializers import SerializeFormat

ArgType = Union[float, int, str, bool, None]
"""Allowable types model arguments"""

# Recursive type definition is not fixed with PEP 563, so ForwardRef type is required.
ModelArgs = Mapping[str, Union["ModelArgs", ArgType]]
"""A mapping of argument names to argument values"""

# https://github.com/python-attrs/cattrs/issues/201
ModelArgs.__args__[1].__args__[0]._evaluate(globals(), locals(), recursive_guard=set())  # type: ignore
conversion.register_structure_hook_func(
    lambda t: t.__class__ is ForwardRef,
    lambda v, t: conversion.converters[SerializeFormat.YAML].structure(
        v, t.__forward_value__
    ),
    which=(SerializeFormat.YAML,),
)

# Leave type-casting to the JSON/YAML serializer
conversion.register_structure_hook(cl=ArgType, func=lambda d, t: d)
