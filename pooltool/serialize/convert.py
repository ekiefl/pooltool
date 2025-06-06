from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, TypeVar

from attrs import define
from cattrs.converters import Converter
from cattrs.dispatch import HookFactory, StructureHook, UnstructureHook
from cattrs.fns import Predicate

from pooltool.serialize.serializers import (
    Pathish,
    SerializeFormat,
    deserializers,
    serializers,
)

T = TypeVar("T")


@define
class Convert:
    converters: dict[SerializeFormat, Converter]

    def __getitem__(self, key: SerializeFormat) -> Converter:
        return self.converters[key]

    def register_structure_hook(
        self,
        cl: Any,
        func: Callable[[Any, type[T]], T],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_structure_hook(cl, func)

    def register_structure_hook_func(
        self,
        check_func: Callable[[type[T]], bool],
        func: Callable[[Any, type[T]], T],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_structure_hook_func(check_func, func)

    def register_structure_hook_factory(
        self,
        check_func: Predicate,
        factory: HookFactory[StructureHook],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_structure_hook_factory(check_func, factory)

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

    def register_unstructure_hook_factory(
        self,
        check_func: Predicate,
        factory: HookFactory[UnstructureHook],
        which: Iterable[SerializeFormat] = SerializeFormat,
    ) -> None:
        for fmt in which:
            self.converters[fmt].register_unstructure_hook_factory(check_func, factory)

    def unstructure_to(self, obj: Any, path: Pathish, fmt: str | None = None) -> None:
        fmt = SerializeFormat(fmt) if fmt is not None else self._infer_ext(path)
        serializers[fmt](self.converters[fmt].unstructure(obj), path)

    def structure_from(self, path: Pathish, cl: type[T], fmt: str | None = None) -> T:
        assert Path(path).exists()
        fmt = SerializeFormat(fmt) if fmt is not None else self._infer_ext(path)
        return self.converters[fmt].structure(deserializers[fmt](path), cl)

    def _infer_ext(self, path: Pathish) -> SerializeFormat:
        inferred = Path(path).suffix.lstrip(".")
        for fmt in self.converters:
            if inferred == fmt.ext:
                return fmt
        raise ValueError(f"Converter object doesn't support extension: '{inferred}'")
