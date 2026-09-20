"""The rendered table's outer extent."""

import attrs


@attrs.define(frozen=True)
class TableBox:
    """The table's outer extent as an axis-aligned box, plus the floor around it.

    Attributes:
        x_min: Outer edge of the rails on the low-x side.
        x_max: Outer edge of the rails on the high-x side.
        y_min: Outer edge of the rails on the low-y side.
        y_max: Outer edge of the rails on the high-y side.
        top: Height of the rail top, in the same frame as ball positions.
        floor: Height of the floor surrounding the table.
    """

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    top: float
    floor: float

    def contains(self, x: float, y: float) -> bool:
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def contains_inset(self, x: float, y: float, inset: float) -> bool:
        """Whether ``(x, y)`` lies at least ``inset`` inside the outline"""
        return (
            self.x_min + inset < x < self.x_max - inset
            and self.y_min + inset < y < self.y_max - inset
        )
