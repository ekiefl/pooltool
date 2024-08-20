from __future__ import annotations

from typing import Dict, Optional, Tuple

from attrs import define, evolve, field

from pooltool.game.datatypes import GameType
from pooltool.objects.table.collection import (
    TableName,
    default_specs_from_game_type,
    default_specs_from_table_type,
    prebuilt_specs,
)
from pooltool.objects.table.components import CushionSegments, Pocket
from pooltool.objects.table.layout import (
    create_billiard_table_cushion_segments,
    create_pocket_table_cushion_segments,
    create_pocket_table_pockets,
)
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
    """A table.

    While a table can be constructed by passing all of the following initialization
    parameters, there are many easier ways, all of which are detailed in the `Table
    Specification </resources/table_specs>` resource.

    Attributes:
        cushion_segments:
            The table's linear and circular cushion segments.
        pockets:
            The table's pockets.
        table_type:
            An Enum specifying the type of table.
        height:
            The height of the playing surface (measured from the ground).

            This is just used for visualization.
        lights_height:
            The height of the table lights (measured from the playing surface).

            This is just used for visualization.
    """

    cushion_segments: CushionSegments
    pockets: Dict[str, Pocket]
    table_type: TableType
    model_descr: Optional[TableModelDescr] = field(default=None)
    height: float = field(default=0.708)
    lights_height: float = field(default=1.99)

    @property
    def w(self) -> float:
        """The width of the table.

        Warning:
            This assumes the table follows the layout similar to `this diagram
            <https://ekiefl.github.io/images/pooltool/pooltool-alg/cushion_count.jpg>`_.
            Specifically, it must have the linear cushion segments with IDs ``"3"``` and
            ``"12"``.
        """

        assert "12" in self.cushion_segments.linear
        assert "3" in self.cushion_segments.linear
        x2 = self.cushion_segments.linear["12"].p1[0]
        x1 = self.cushion_segments.linear["3"].p1[0]
        return x2 - x1

    @property
    def l(self) -> float:  # noqa F743
        """The length of the table.

        Warning:
            This assumes the table follows the layout similar to `this diagram
            <https://ekiefl.github.io/images/pooltool/pooltool-alg/cushion_count.jpg>`_.
            Specifically, it must have the linear cushion segments with IDs ``"9"``` and
            ``"18"``.
        """
        assert "9" in self.cushion_segments.linear
        assert "18" in self.cushion_segments.linear
        y2 = self.cushion_segments.linear["9"].p1[1]
        y1 = self.cushion_segments.linear["18"].p1[1]
        return y2 - y1

    @property
    def center(self) -> Tuple[float, float]:
        """Return the 2D coordinates of the table's center

        Warning:
            This assumes :meth:`l` and :meth:`w` are defined.
        """

        return self.w / 2, self.l / 2

    @property
    def has_linear_cushions(self) -> bool:
        return bool(len(self.cushion_segments.linear))

    @property
    def has_circular_cushions(self) -> bool:
        return bool(len(self.cushion_segments.circular))

    @property
    def has_pockets(self) -> bool:
        return bool(len(self.pockets))

    def copy(self) -> Table:
        """Create a copy."""
        # Delegates the deep-ish copying of CushionSegments and Pocket to their respective
        # copy() methods. Uses dictionary comprehension to construct equal but different
        # `pockets` attribute.  All other attributes are frozen or immutable.
        return evolve(
            self,
            cushion_segments=self.cushion_segments.copy(),
            pockets={k: v.copy() for k, v in self.pockets.items()},
        )

    @staticmethod
    def from_table_specs(specs: TableSpecs) -> Table:
        """Build a table from a table specifications object

        Args:
            specs:
                A valid table specification.

                Accepted objects:
                    - :class:`pooltool.objects.table.specs.PocketTableSpecs`
                    - :class:`pooltool.objects.table.specs.BilliardTableSpecs`
                    - :class:`pooltool.objects.table.specs.SnookerTableSpecs`

        Returns:
            Table:
                A table matching the specifications of the input.

                - :class:`pooltool.objects.table.specs.PocketTableSpecs` has
                  :attr:`table_type` set to `pooltool.objects.table.specs.TableType.POCKET`
                - :class:`pooltool.objects.table.specs.BilliardTableSpecs` has
                  :attr:`table_type` set to `pooltool.objects.table.specs.TableType.BILLIARD`
                - :class:`pooltool.objects.table.specs.SnookerTableSpecs` has
                  :attr:`table_type` set to `pooltool.objects.table.specs.TableType.SNOOKER`
        """
        if specs.table_type == TableType.BILLIARD:
            assert isinstance(specs, BilliardTableSpecs)
            segments = create_billiard_table_cushion_segments(specs)
            pockets = {}
        elif (
            specs.table_type == TableType.POCKET
            or specs.table_type == TableType.SNOOKER
        ):
            assert isinstance(specs, PocketTableSpecs)
            segments = create_pocket_table_cushion_segments(specs)
            pockets = create_pocket_table_pockets(specs)
        else:
            raise NotImplementedError(f"Unknown table type: {specs.table_type}")

        return Table(
            cushion_segments=segments,
            pockets=pockets,
            table_type=specs.table_type,
            model_descr=specs.model_descr,
            height=specs.height,
            lights_height=specs.lights_height,
        )

    @classmethod
    def prebuilt(cls, name: TableName) -> Table:
        """Create a default table based on name

        Args:
            name:
                The name of the prebuilt table specs.

        Returns:
            Table:
                A prebuilt table.
        """
        return cls.from_table_specs(prebuilt_specs(name))

    @classmethod
    def default(cls, table_type: TableType = TableType.POCKET) -> Table:
        """Create a default table based on table type

        A default table is associated to each table type.

        Args:
            table_type:
                The type of table.

        Returns:
            Table:
                The default table for the given table type.
        """
        return cls.from_table_specs(default_specs_from_table_type(table_type))

    @classmethod
    def from_game_type(cls, game_type: GameType) -> Table:
        """Create a default table based on table type

        A default table is associated with each game type.

        Args:
            game_type:
                The game type.

        Returns:
            Table:
                The default table for the given game type.
        """
        return cls.from_table_specs(default_specs_from_game_type(game_type))


__all__ = [
    "BilliardTableSpecs",
    "PocketTableSpecs",
    "SnookerTableSpecs",
    "TableModelDescr",
    "TableSpecs",
    "TableType",
]
