from __future__ import annotations

from typing import Dict, Optional, Tuple

from attrs import define, evolve, field

from pooltool.game.datatypes import GameType
from pooltool.objects.table.collection import (
    TableName,
    get_default_specs,
    prebuilt_specs,
)
from pooltool.objects.table.components import CushionSegments, Pocket
from pooltool.objects.table.specs import (
    BilliardTableSpecs,
    PocketTableSpecs,
    SnookerTableSpecs,
    TableModelDescr,
    TableSpecs,
    TableType,
)


@define
class Table:
    cushion_segments: CushionSegments
    pockets: Dict[str, Pocket]
    table_type: TableType
    model_descr: Optional[TableModelDescr] = field(default=None)
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)

    @property
    def w(self) -> float:
        """The width of the table"""
        x2 = self.cushion_segments.linear["12"].p1[0]
        x1 = self.cushion_segments.linear["3"].p1[0]
        return x2 - x1

    @property
    def l(self) -> float:
        """The length of the table"""
        y2 = self.cushion_segments.linear["9"].p1[1]
        y1 = self.cushion_segments.linear["18"].p1[1]
        return y2 - y1

    @property
    def center(self) -> Tuple[float, float]:
        return self.w / 2, self.l / 2

    def copy(self) -> Table:
        """Create a deep-ish copy

        Delegates the deep-ish copying of CushionSegments and Pocket to their respective
        copy() methods. Uses dictionary comprehension to construct equal but different
        `pockets` attribute.  All other attributes are frozen or immutable.
        """
        return evolve(
            self,
            cushion_segments=self.cushion_segments.copy(),
            pockets={k: v.copy() for k, v in self.pockets.items()},
        )

    @staticmethod
    def from_table_specs(specs: TableSpecs) -> Table:
        return Table(
            cushion_segments=specs.create_cushion_segments(),
            pockets=specs.create_pockets(),
            table_type=specs.table_type,
            model_descr=specs.model_descr,
            height=specs.height,
            lights_height=specs.lights_height,
        )

    @classmethod
    def prebuilt(cls, name: TableName) -> Table:
        return cls.from_table_specs(prebuilt_specs(name))

    @classmethod
    def default(cls, table_type: TableType = TableType.POCKET) -> Table:
        return cls.from_table_specs(get_default_specs(table_type))

    @classmethod
    def from_game_type(cls, game_type: GameType) -> Table:
        _game_table_type_map: Dict[GameType, TableType] = {
            GameType.EIGHTBALL: TableType.POCKET,
            GameType.NINEBALL: TableType.POCKET,
            GameType.THREECUSHION: TableType.BILLIARD,
            GameType.SUMTOTHREE: TableType.BILLIARD,
            GameType.SNOOKER: TableType.SNOOKER,
            GameType.SANDBOX: TableType.POCKET,
        }

        return cls.default(_game_table_type_map[game_type])


__all__ = [
    "BilliardTableSpecs",
    "PocketTableSpecs",
    "SnookerTableSpecs",
    "TableModelDescr",
    "TableSpecs",
    "TableType",
]
