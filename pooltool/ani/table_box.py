"""The rendered table's outer extent."""

import attrs
import numpy as np
from numpy.typing import NDArray


@attrs.define(frozen=True)
class TableBox:
    """The table's outer extent as an axis-aligned box, plus the floor around it.

    The playing surface spans ``0 <= x <= w`` and ``0 <= y <= l`` at height zero. The
    cushions and rails extend beyond it to the box outline, with their tops flush at
    ``top``.

    Attributes:
        w: Width of the playing surface.
        l: Length of the playing surface.
        x_min: Outer edge of the rails on the low-x side.
        x_max: Outer edge of the rails on the high-x side.
        y_min: Outer edge of the rails on the low-y side.
        y_max: Outer edge of the rails on the high-y side.
        top: Height of the rail top, in the same frame as ball positions.
        floor: Height of the floor surrounding the table.
    """

    w: float
    l: float
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    top: float
    floor: float

    def contains(self, x: float, y: float) -> bool:
        """Whether ``(x, y)`` lies within the rail outline"""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def surface_heights(
        self, xyz: NDArray[np.float64], R: float
    ) -> NDArray[np.float64]:
        """The height of the surface under a ball at each position

        Over the playing surface that is the cloth, and over the rails it is the rail
        top when the ball is above it. Beyond the rails it is the floor. A ball below
        the cloth, which is one dropping into a pocket, has no surface under it, and
        the value follows the ball's bottom instead.
        """
        x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        bottom = z - R
        cloth = np.minimum(0.0, bottom)

        over_playing_surface = (0.0 <= x) & (x <= self.w) & (0.0 <= y) & (y <= self.l)
        inside_outline = (
            (self.x_min <= x)
            & (x <= self.x_max)
            & (self.y_min <= y)
            & (y <= self.y_max)
        )
        on_rail = inside_outline & ~over_playing_surface & (bottom >= self.top)
        follows_ball = over_playing_surface | (inside_outline & (bottom < self.top))

        heights = np.full(len(xyz), self.floor)
        heights[on_rail] = self.top
        heights[follows_ball] = cloth[follows_ball]
        return heights
