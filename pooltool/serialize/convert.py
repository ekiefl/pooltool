from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Type, TypeVar

from attrs import define
from cattrs.converters import Converter

from pooltool.serialize.serializers import (
    Pathish,
    SerializeFormat,
    deserializers,
    serializers,
)

T = TypeVar("T")


@define
class Convert:
    converters: Dict[SerializeFormat, Converter]

    def __getitem__(self, key: SerializeFormat) -> Converter:
        return self.converters[key]

    def register_structure_hook(
        self,
        cl: Any,
        func: Callable[[Any, Type[T]], T],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_structure_hook(cl, func)

    def register_structure_hook_func(
        self,
        check_func: Callable[[Type[T]], bool],
        func: Callable[[Any, Type[T]], T],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_structure_hook_func(check_func, func)

    def register_unstructure_hook(
        self,
        cls: Any,
        func: Callable[[Any], Any],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_unstructure_hook(cls, func)

    def register_unstructure_hook_func(
        self,
        check_func: Callable[[Any], bool],
        func: Callable[[Any], Any],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_unstructure_hook_func(check_func, func)

    def unstructure_to(
        self, obj: Any, path: Pathish, fmt: Optional[str] = None
    ) -> None:
        fmt = SerializeFormat(fmt) if fmt is not None else self._infer_ext(path)
        serializers[fmt](self.converters[fmt].unstructure(obj), path)

    def structure_from(
        self, path: Pathish, cl: Type[T], fmt: Optional[str] = None
    ) -> T:
        assert Path(path).exists()
        fmt = SerializeFormat(fmt) if fmt is not None else self._infer_ext(path)
        return self.converters[fmt].structure(deserializers[fmt](path), cl)

    def _infer_ext(self, path: Pathish) -> SerializeFormat:
        inferred = Path(path).suffix.lstrip(".")
        for fmt in self.converters:
            if inferred == fmt.ext:
                return fmt
        raise ValueError(f"Converter object doesn't support extension: '{inferred}'")
