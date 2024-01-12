#! /usr/bin/env python

from __future__ import annotations

from typing import Dict, Protocol

from attrs import define, field

import pooltool.ani as ani
from pooltool.error import ConfigError
from pooltool.objects.table.components import CushionSegments, Pocket
from pooltool.objects.table.layout import (
    create_billiard_table_cushion_segments,
    create_pocket_table_cushion_segments,
    create_pocket_table_pockets,
)
from pooltool.utils import panda_path, strenum


@define(frozen=True)
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


class TableType(strenum.StrEnum):
    POCKET = strenum.auto()
    BILLIARD = strenum.auto()
    SNOOKER = strenum.auto()


@define
class TableSpecs(Protocol):
    @property
    def table_type(self) -> TableType:
        ...

    @property
    def height(self) -> float:
        ...

    @property
    def lights_height(self) -> float:
        ...

    @property
    def model_descr(self) -> TableModelDescr:
        ...

    def create_cushion_segments(self) -> CushionSegments:
        ...

    def create_pockets(self) -> Dict[str, Pocket]:
        ...


@define(frozen=True)
class PocketTableSpecs(TableSpecs):
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
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)
    model_descr: TableModelDescr = field(factory=TableModelDescr.null)

    table_type: TableType = field(init=False, default=TableType.POCKET)

    def create_cushion_segments(self) -> CushionSegments:
        return create_pocket_table_cushion_segments(self)

    def create_pockets(self) -> Dict[str, Pocket]:
        return create_pocket_table_pockets(self)


@define(frozen=True)
class BilliardTableSpecs(TableSpecs):
    """Parameters that specify a billiard (pocketless) table"""

    # 10-foot table (imprecise)
    l: float = field(default=3.05)
    w: float = field(default=3.05 / 2)

    # FIXME height should be adjusted for 3-cushion sized balls
    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)

    # For visualization
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)
    model_descr: TableModelDescr = field(factory=TableModelDescr.null)

    table_type: TableType = field(init=False, default=TableType.BILLIARD)

    def create_cushion_segments(self) -> CushionSegments:
        return create_billiard_table_cushion_segments(self)

    def create_pockets(self) -> Dict[str, Pocket]:
        return {}


@define(frozen=True)
class SnookerTableSpecs(TableSpecs):
    """Parameters that specify a snooker table

    NOTE Currently, the SnookerTableSpecs class is an identical clone of
    PocketTableSpecs, but with different defaults. That's not very useful, but
    it's likely that some time in the future, snooker tables may have some
    parameters distinct from standard pool tables (e.g. directional cloth). For
    this reason, let's keep SnookerTableSpecs.
    """

    # https://wpbsa.com/rules/
    # The playing area is within the cushion faces and shall measure
    # 11 ft 8½ in x 5 ft 10 in (3569 mm x 1778 mm) with a tolerance on both dimensions of +/- ½ in (13 mm).
    l: float = field(default=3.566)  # my table size
    w: float = field(default=1.770)  # my table size

    cushion_width: float = field(default=2 * 25.4 / 1000)
    cushion_height: float = field(default=0.04)
    corner_pocket_width: float = field(default=0.083)
    corner_pocket_angle: float = field(default=0)  # degrees  # TODO how to measure that
    corner_pocket_depth: float = field(default=0.04)
    corner_pocket_radius: float = field(default=4 * 25.4 / 1000)
    corner_jaw_radius: float = field(default=4 * 25.4 / 1000)
    side_pocket_width: float = field(default=0.087)
    side_pocket_angle: float = field(default=0)  # degrees # TODO how to measure that
    side_pocket_depth: float = field(default=0.004)
    side_pocket_radius: float = field(default=2 * 25.4 / 1000)
    side_jaw_radius: float = field(default=3 * 25.4 / 1000)

    # For visualization
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)
    model_descr: TableModelDescr = field(factory=TableModelDescr.null)

    table_type: TableType = field(init=False, default=TableType.SNOOKER)

    def create_cushion_segments(self) -> CushionSegments:
        return create_pocket_table_cushion_segments(self)

    def create_pockets(self) -> Dict[str, Pocket]:
        return create_pocket_table_pockets(self)
