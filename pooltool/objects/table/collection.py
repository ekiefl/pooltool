from typing import Dict

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


TABLE_SPECS: Dict[TableName, TableSpecs] = {
    TableName.SEVEN_FOOT_SHOWOOD: PocketTableSpecs(
        l=1.9812,
        w=1.9812 / 2,
        cushion_width=2 * 2.54 / 100,
        cushion_height=0.64 * 2 * 0.028575,
        corner_pocket_width=0.118,
        corner_pocket_angle=5.3,
        corner_pocket_depth=0.0398,
        corner_pocket_radius=0.124 / 2,
        corner_jaw_radius=0.0419 / 2,
        side_pocket_width=0.137,
        side_pocket_angle=7.14,
        side_pocket_depth=0.00437,
        side_pocket_radius=0.129 / 2,
        side_jaw_radius=0.0159 / 2,
        height=0.708,
        lights_height=1.99,
        model_descr=TableModelDescr(name="seven_foot_showood"),
    ),
    TableName.SNOOKER_GENERIC: SnookerTableSpecs(
        l=3.5869,
        w=1.778,
        cushion_width=2 * 2.54 / 100,
        cushion_height=0.64 * 2 * 0.028575,
        corner_pocket_width=0.118,
        corner_pocket_angle=5.3,
        corner_pocket_depth=0.0398,
        corner_pocket_radius=0.124 / 2,
        corner_jaw_radius=0.0419 / 2,
        side_pocket_width=0.137,
        side_pocket_angle=7.14,
        side_pocket_depth=0.00437,
        side_pocket_radius=0.129 / 2,
        side_jaw_radius=0.0159 / 2,
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
}


_default_map: Dict[TableType, TableName] = {
    TableType.POCKET: TableName.SEVEN_FOOT_SHOWOOD,
    TableType.SNOOKER: TableName.SNOOKER_GENERIC,
    TableType.BILLIARD: TableName.BILLIARD_WIP,
}


def get_default_specs(table_type: TableType) -> TableSpecs:
    return prebuilt_specs(_default_map[table_type])


def prebuilt_specs(name: TableName) -> TableSpecs:
    return TABLE_SPECS[name]
