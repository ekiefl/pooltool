#! /usr/bin/env python

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol

import pooltool.ani as ani
from pooltool.error import ConfigError
from pooltool.objects.table._layout import (
    _create_billiard_table_cushion_segments,
    _create_pocket_table_cushion_segments,
    _create_pocket_table_pockets,
)
from pooltool.objects.table.components import CushionSegments, Pocket
from pooltool.utils import panda_path, strenum


@dataclass(frozen=True)
class TableModelDescr:
    name: str

    @property
    def path(self):
        """The path of the model

        The path is searched for in pooltool/models/table/{name}/{name}[_pbr].glb. If
        physical based rendering (PBR) is requested, a model suffixed with _pbr will be
        looked for. ConfigError is raised if model path cannot be determined from name.
        """

        if ani.settings["graphics"]["physical_based_rendering"]:
            path = ani.model_dir / "table" / self.name / (self.name + "_pbr.glb")
        else:
            path = ani.model_dir / "table" / self.name / (self.name + ".glb")

        if not path.exists():
            raise ConfigError(f"Couldn't find table model with name: {self.name}")

        return panda_path(path)

    @staticmethod
    def null() -> TableModelDescr:
        return TableModelDescr(name="null")

    @staticmethod
    def pocket_table_default() -> TableModelDescr:
        return TableModelDescr(name="7_foot")

    @staticmethod
    def billiard_table_default() -> TableModelDescr:
        return TableModelDescr.null()


class TableType(strenum.StrEnum):
    POCKET = strenum.auto()
    BILLIARD = strenum.auto()


@dataclass(frozen=True)
class PocketTableSpecs:
    """Parameters that specify a pocket table"""

    # 7-foot table (78x39 in^2 playing surface)
    l: float = field(default=1.9812)
    w: float = field(default=1.9812 / 2)

    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)
    corner_pocket_width: float = field(default=0.118)
    corner_pocket_angle: float = field(default=5.3)  # degrees
    corner_pocket_depth: float = field(default=0.0398)
    corner_pocket_radius: float = field(default=0.124 / 2)
    corner_jaw_radius: float = field(default=0.0419 / 2)
    side_pocket_width: float = field(default=0.137)
    side_pocket_angle: float = field(default=7.14)  # degrees
    side_pocket_depth: float = field(default=0.00437)
    side_pocket_radius: float = field(default=0.129 / 2)
    side_jaw_radius: float = field(default=0.0159 / 2)

    # For visualization
    model_descr: Optional[TableModelDescr] = None
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)

    table_type: TableType = field(init=False, default=TableType.POCKET)

    def __post_init__(self):
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if field.init
        }

        if all(
            getattr(self, fname) == default for fname, default in field_defaults.items()
        ):
            # All parameters match the default table, and so the TableModelDescr is used
            # even if it wasn't explictly requested.
            object.__setattr__(
                self, "model_descr", TableModelDescr.pocket_table_default()
            )

    def create_cushion_segments(self) -> CushionSegments:
        return _create_pocket_table_cushion_segments(self)

    def create_pockets(self) -> Dict[str, Pocket]:
        return _create_pocket_table_pockets(self)


@dataclass(frozen=True)
class BilliardTableSpecs:
    """Parameters that specify a billiard (pocketless) table"""

    # 10-foot table (imprecise)
    l: float = field(default=3.05)
    w: float = field(default=3.05 / 2)

    # FIXME height should be adjusted for 3-cushion sized balls
    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)

    # For visualization
    model_descr: Optional[TableModelDescr] = None
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)

    table_type: TableType = field(init=False, default=TableType.BILLIARD)

    def __post_init__(self):
        field_defaults = {
            fname: field.default
            for fname, field in self.__dataclass_fields__.items()
            if field.init
        }

        if all(
            getattr(self, fname) == default for fname, default in field_defaults.items()
        ):
            # All parameters match the default table, and so the TableModelDescr is used
            # even if it wasn't explictly requested.
            self.model_descr = TableModelDescr.billiard_table_default()

    def create_cushion_segments(self) -> CushionSegments:
        return _create_billiard_table_cushion_segments(self)

    def create_pockets(self) -> Dict[str, Pocket]:
        return {}


class TableSpecs(Protocol):
    l: float
    w: float

    def create_cushion_segments(self):
        ...

    def create_pockets(self):
        ...


@dataclass
class Table:
    specs: TableSpecs
    cushion_segments: CushionSegments
    pockets: Dict[str, Pocket]

    @property
    def w(self) -> float:
        return self.specs.w

    @property
    def l(self) -> float:
        return self.specs.l

    @property
    def center(self):
        return self.w / 2, self.l / 2

    @staticmethod
    def from_table_specs(specs: TableSpecs) -> Table:
        return Table(
            specs=specs,
            cushion_segments=specs.create_cushion_segments(),
            pockets=specs.create_pockets(),
        )

    @staticmethod
    def pocket_table() -> Table:
        return Table.from_table_specs(PocketTableSpecs())

    @staticmethod
    def billiard_table() -> Table:
        return Table.from_table_specs(BilliardTableSpecs())

    @staticmethod
    def default() -> Table:
        return Table.pocket_table()
