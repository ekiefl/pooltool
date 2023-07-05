from typing import Mapping, Union

from pooltool.serialize import conversion

ArgType = Union[float, int, str, bool]
ModelArgs = Mapping[str, ArgType]

# Leave type-casting to the JSON/YAML serializer
conversion.register_structure_hook(cl=ArgType, func=lambda d, t: d)
