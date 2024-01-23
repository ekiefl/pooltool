from typing import Dict

from pooltool.game.datatypes import GameType
from pooltool.objects.table.specs import (
    BilliardTableSpecs,
    PocketTableSpecs,
    SnookerTableSpecs,
    TableModelDescr,
    TableSpecs,
    TableType,
)
from pooltool.utils.strenum import StrEnum, auto


class TableName(StrEnum):
    SEVEN_FOOT_SHOWOOD = auto()
    SNOOKER_GENERIC = auto()
    BILLIARD_WIP = auto()
    SUMTOTHREE_WIP = auto()


TABLE_SPECS: Dict[TableName, TableSpecs] = {
    TableName.SEVEN_FOOT_SHOWOOD: PocketTableSpecs(
        l=1.9812,
        w=1.9812 / 2,
        cushion_width=2 * 2.54 / 100,
        cushion_height=0.64 * 2 * 0.028575,
        corner_pocket_width=0.118,
        corner_pocket_angle=5.3,
        corner_pocket_depth=0.0417,
        corner_pocket_radius=0.062,
        corner_jaw_radius=0.02095,
        side_pocket_width=0.137,
        side_pocket_angle=7.14,
        side_pocket_depth=0.0685,
        side_pocket_radius=0.0645,
        side_jaw_radius=0.00795,
        height=0.708,
        lights_height=1.99,
        model_descr=TableModelDescr(name="seven_foot_showood"),
    ),
    TableName.SNOOKER_GENERIC: SnookerTableSpecs(
        l=3.5445,
        w=1.7465,
        cushion_width=1.55 * 25.4 / 1000,
        cushion_height=0.028,
        corner_pocket_width=0.083,
        corner_pocket_angle=0,
        corner_pocket_depth=0.036,
        corner_pocket_radius=0.043,
        corner_jaw_radius=3.6 * 25.4 / 1000,
        side_pocket_width=0.075,
        side_pocket_angle=0,
        side_pocket_depth=0.95 * 25.4 / 1000,
        side_pocket_radius=1.68 * 25.4 / 1000,
        side_jaw_radius=2.5 * 25.4 / 1000,
        height=0.708,
        lights_height=1.99,
        model_descr=TableModelDescr(name="snooker_generic"),
    ),
    TableName.BILLIARD_WIP: BilliardTableSpecs(
        l=3.05,
        w=3.05 / 2,
        cushion_width=2 * 2.54 / 100,
        cushion_height=0.64 * 2 * 0.028575,
        height=0.708,
        lights_height=1.99,
        model_descr=TableModelDescr.null(),
    ),
    TableName.SUMTOTHREE_WIP: BilliardTableSpecs(
        l=3.05 / 2.5,
        w=3.05 / 2 / 2.5,
        cushion_width=2 * 2.54 / 100,
        cushion_height=0.64 * 2 * 0.028575,
        height=0.708,
        lights_height=1.99,
        model_descr=TableModelDescr.null(),
    ),
}


_default_table_type_map: Dict[TableType, TableName] = {
    TableType.POCKET: TableName.SEVEN_FOOT_SHOWOOD,
    TableType.SNOOKER: TableName.SNOOKER_GENERIC,
    TableType.BILLIARD: TableName.BILLIARD_WIP,
}

_default_game_type_map: Dict[GameType, TableName] = {
    GameType.EIGHTBALL: TableName.SEVEN_FOOT_SHOWOOD,
    GameType.NINEBALL: TableName.SEVEN_FOOT_SHOWOOD,
    GameType.SNOOKER: TableName.SNOOKER_GENERIC,
    GameType.THREECUSHION: TableName.BILLIARD_WIP,
    GameType.SUMTOTHREE: TableName.SUMTOTHREE_WIP,
}


def default_specs_from_table_type(table_type: TableType) -> TableSpecs:
    return prebuilt_specs(_default_table_type_map[table_type])


def default_specs_from_game_type(game_type: GameType) -> TableSpecs:
    return prebuilt_specs(_default_game_type_map[game_type])


def prebuilt_specs(name: TableName) -> TableSpecs:
    return TABLE_SPECS[name]
