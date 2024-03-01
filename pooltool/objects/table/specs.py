#! /usr/bin/env python

from __future__ import annotations

from typing import Protocol

from attrs import define, field

import pooltool.ani as ani
from pooltool.error import ConfigError
from pooltool.utils import panda_path, strenum


@define(frozen=True)
class TableModelDescr:
    """A table model specifier

    Attributes:
        name:
            The name of the table model.
    """

    name: str

    @property
    def path(self) -> str:
        """The path of the model

        The path is searched for in ``pooltool/models/table/{name}/{name}[_pbr].glb``.
        If physical based rendering (PBR) is requested, a model suffixed with _pbr will
        be looked for.

        Raises:
            ConfigError:
                If model path cannot be found from name.

        Returns:
            str:
                A filename specified with Panda3D filename syntax (see
                https://docs.panda3d.org/1.10/python/programming/advanced-loading/filename-syntax).
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
    """An Enum describing the table type"""

    POCKET = strenum.auto()
    BILLIARD = strenum.auto()
    SNOOKER = strenum.auto()
    OTHER = strenum.auto()


class TableSpecs(Protocol):
    @property
    def table_type(self) -> TableType: ...

    @property
    def height(self) -> float: ...

    @property
    def lights_height(self) -> float: ...

    @property
    def model_descr(self) -> TableModelDescr: ...


@define(frozen=True)
class PocketTableSpecs:
    """Parameter specifications for a pocket table.

    See Also:
        - See the :doc:`Table Specification </resources/table_specs>` resource for
          visualizations and descriptions of each attribute.
        - See :class:`BilliardTableSpecs` for billiard table specs.
        - See :class:`SnookerTableSpecs` for pocket table specs.
    """

    # 7-foot table (78x39 in^2 playing surface)
    l: float = field(default=1.9812)  # noqa  E741
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


@define(frozen=True)
class BilliardTableSpecs:
    """Parameter specifications for a billiards (pocketless) table.

    See Also:
        - See the :doc:`Table Specification </resources/table_specs>` resource for
          visualizations and descriptions of each attribute.
        - See :class:`PocketTableSpecs` for billiard table specs.
        - See :class:`SnookerTableSpecs` for pocket table specs.
    """

    # 10-foot table (imprecise)
    l: float = field(default=3.05)  # noqa  E741
    w: float = field(default=3.05 / 2)

    # FIXME height should be adjusted for 3-cushion sized balls
    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)

    # For visualization
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)
    model_descr: TableModelDescr = field(factory=TableModelDescr.null)

    table_type: TableType = field(init=False, default=TableType.BILLIARD)


@define(frozen=True)
class SnookerTableSpecs:
    """Parameter specifications for a snooker table.

    See Also:
        - See the :doc:`Table Specification </resources/table_specs>` resource for
          visualizations and descriptions of each attribute.
        - See :class:`BilliardTableSpecs` for billiard table specs.
        - See :class:`PocketTableSpecs` for pocket table specs.

    Note:
        Currently, this class is an identical clone of :class:`PocketTableSpecs`, but
        with different defaults. That's not very useful, but it's likely that some time
        in the future, snooker tables may have some parameters distinct from standard
        pool tables (*e.g.* directional cloth), causing these classes to diverge.
    """

    # https://wpbsa.com/rules/
    # The playing area is within the cushion faces and shall measure
    # 11 ft 8½ in x 5 ft 10 in (3569 mm x 1778 mm) with a tolerance on both dimensions of +/- ½ in (13 mm).
    l: float = field(default=3.5445)  # noqa  E741
    w: float = field(default=1.7465)

    cushion_width: float = field(default=1.55 * 25.4 / 1000)
    cushion_height: float = field(default=0.028)
    corner_pocket_width: float = field(default=0.083)
    corner_pocket_angle: float = field(default=0)
    corner_pocket_depth: float = field(default=0.036)
    corner_pocket_radius: float = field(default=4 * 25.4 / 1000)
    corner_jaw_radius: float = field(default=4 * 25.4 / 1000)
    side_pocket_width: float = field(default=0.087)
    side_pocket_angle: float = field(default=0)
    side_pocket_depth: float = field(default=0.95 * 25.4 / 1000)
    side_pocket_radius: float = field(default=1.68 * 25.4 / 1000)
    side_jaw_radius: float = field(default=2.5 * 25.4 / 1000)

    # For visualization
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)
    model_descr: TableModelDescr = field(factory=TableModelDescr.null)

    table_type: TableType = field(init=False, default=TableType.SNOOKER)
