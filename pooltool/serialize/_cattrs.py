import cattrs
import numpy as np

converter = cattrs.GenConverter()

# https://github.com/python-attrs/cattrs/issues/194
converter.register_structure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda v, t: np.array([t.__args__[1].__args[0](e) for e in v]),
)
converter.register_unstructure_hook_func(
    lambda t: getattr(t, "__origin__", None) is np.ndarray,
    lambda array: array.tolist(),
)
