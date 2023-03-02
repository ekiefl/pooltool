from pooltool.serialize.convert import Convert
from pooltool.serialize.serializers import SerializeFormat, to_json, to_msgpack, from_json, from_msgpack
import numpy as np
from cattrs.preconf.json import make_converter as make_json_converter
from cattrs.preconf.msgpack import make_converter as make_msgpack_converter
from pooltool.utils.strenum import StrEnum

conversion = Convert(
    {
        SerializeFormat.JSON: make_json_converter(),
        SerializeFormat.MSGPACK: make_msgpack_converter(),
    }
)

# Numpy arrays
# https://github.com/python-attrs/cattrs/issues/194
conversion.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: np.array([t.__args__[1].__args__[0](e) for e in v]),
    which=(SerializeFormat.JSON,),
)

# msgpack arrays are already arrays, simply return oneself
conversion.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: v,
    which=(SerializeFormat.MSGPACK,),
)

# JSON needs to unstructure numpy arrays as lists
conversion.register_unstructure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda array: array.tolist(),
    which=(SerializeFormat.JSON,),
)

# StrEnum
conversion.register_unstructure_hook(
    StrEnum,
    lambda v: v.value,
)
