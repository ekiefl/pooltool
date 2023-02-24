import cattrs
import numpy as np

# from pooltool.utils.strenum import StrEnum

converter = cattrs.GenConverter()

# Numpy arrays
# https://github.com/python-attrs/cattrs/issues/194
converter.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: np.array([t.__args__[1].__args__[0](e) for e in v]),
)
converter.register_unstructure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda array: array.tolist(),
)

## StrEnum
# converter.register_structure_hook(
#    StrEnum, lambda v: StrEnum(v)
# )
